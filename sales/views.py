from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import CashDrawerShift, SalesOrder
from .serializers import CashDrawerShiftSerializer, SalesOrderSerializer

class CashDrawerShiftViewSet(viewsets.ModelViewSet):
    queryset = CashDrawerShift.objects.order_by('-opened_at')
    serializer_class = CashDrawerShiftSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['store', 'cashier', 'status']

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.select_related('store', 'cashier', 'customer', 'shift').prefetch_related('items__product').order_by('-created_at')
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['store', 'status', 'payment_method']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # Pass cashier implicitly to prevent forged sales
            order = serializer.save(cashier=request.user)

            # Deduct stock
            if order.status == 'Completed':
                for item in order.items.all():
                    product = item.product
                    if product.stock < item.quantity:
                        raise ValueError(f"Insufficient stock for {product.name}")
                    product.stock -= item.quantity
                    product.save(update_fields=['stock'])

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='hold-order')
    def hold_order(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = serializer.save(cashier=request.user, status='Pending')

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
