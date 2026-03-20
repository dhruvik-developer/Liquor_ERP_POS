from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import PurchaseOrder, PurchaseBill, PurchaseReturn
from .serializers import PurchaseOrderSerializer, PurchaseBillSerializer, PurchaseReturnSerializer
from inventory.models import Product

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('vendor').prefetch_related('items').order_by('-created_at')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vendor', 'status']

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        po = self.get_object()
        if po.status == 'Fully Received':
            return Response({"error": "Order already received."}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            for item in po.items.all():
                # For simplicity, assuming full receipt. You could pass partial amounts in request.data
                received_qty = item.quantity_ordered - item.quantity_received
                if received_qty > 0:
                    item.quantity_received += received_qty
                    item.save(update_fields=['quantity_received'])
                    
                    product = item.product
                    product.stock += received_qty
                    product.save(update_fields=['stock'])
            
            po.status = 'Fully Received'
            po.save(update_fields=['status'])
        
        return Response({"message": "Purchase order successfully received and stock updated."})

class PurchaseBillViewSet(viewsets.ModelViewSet):
    queryset = PurchaseBill.objects.select_related('vendor', 'purchase_order').order_by('-created_at')
    serializer_class = PurchaseBillSerializer
    permission_classes = [IsAuthenticated]

class PurchaseReturnViewSet(viewsets.ModelViewSet):
    queryset = PurchaseReturn.objects.select_related('vendor').order_by('-created_at')
    serializer_class = PurchaseReturnSerializer
    permission_classes = [IsAuthenticated]
