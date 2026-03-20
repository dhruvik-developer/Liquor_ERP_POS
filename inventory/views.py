from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import F
from .models import Category, Product, StockAdjustment
from .serializers import CategorySerializer, ProductSerializer, StockAdjustmentSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'vendor').all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category', 'vendor', 'is_active', 'brand']

    def get_queryset(self):
        qs = super().get_queryset()
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            qs = qs.filter(stock__lte=F('low_stock_threshold'))
        return qs

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        queryset = self.get_queryset().filter(stock__lte=F('low_stock_threshold'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class StockAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = StockAdjustment.objects.all()
    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            adjustment = serializer.save(user=request.user)
            product = adjustment.product
            
            if adjustment.adjustment_type == 'add':
                product.stock += adjustment.quantity
            elif adjustment.adjustment_type == 'reduce':
                if product.stock < adjustment.quantity:
                    return Response(
                        {"error": "Insufficient stock for reduction"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.stock -= adjustment.quantity
            
            product.save(update_fields=['stock'])
            
        return Response(serializer.data, status=status.HTTP_201_CREATED)
