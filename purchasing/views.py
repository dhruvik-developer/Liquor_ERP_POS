from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import F
from .models import PurchaseOrder, PurchaseBill, PurchaseReturn
from .serializers import PurchaseOrderSerializer, PurchaseBillSerializer, PurchaseReturnSerializer
from inventory.models import Product, StockAdjustment

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseOrder.objects
        .select_related('vendor', 'vendor__default_tax_class', 'vendor__address')
        .prefetch_related('items')
        .order_by('-created_at')
    )
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vendor', 'status']

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        po = self.get_object()
        if po.status == 'Fully Received':
            return Response({"error": "Order already received."}, status=status.HTTP_400_BAD_REQUEST)

        items_payload = request.data.get('items')

        with transaction.atomic():
            po_items = list(po.items.select_related('product').all())
            stock_fields_available = any(hasattr(item.product, 'stock') for item in po_items if item.product_id)

            if items_payload is None:
                # Backward-compatible behavior: receive all remaining quantity.
                for item in po_items:   
                    received_qty = item.quantity_ordered - item.quantity_received
                    if received_qty <= 0:
                        continue

                    item.quantity_received += received_qty
                    item.save(update_fields=['quantity_received'])

                    if stock_fields_available:
                        Product.objects.filter(pk=item.product_id).update(stock=F('stock') + received_qty)

                        # Create Stock Adjustment record
                        StockAdjustment.objects.create(
                            product_id=item.product_id,
                            user=request.user,
                            adjustment_type='add',
                            quantity=received_qty,
                            reason=f"Received for PO {po.po_number}",
                        )
            else:
                if not isinstance(items_payload, list):
                    return Response(
                        {"error": "items must be a list."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                item_lookup = {item.id: item for item in po_items}
                product_lookup = {item.product_id: item for item in po_items}

                for row in items_payload:
                    if not isinstance(row, dict):
                        return Response(
                            {"error": "Each items entry must be an object."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    received_qty = row.get('received_quantity', row.get('quantity'))
                    if received_qty is None:
                        return Response(
                            {"error": "Each item must include received_quantity."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    try:
                        received_qty = int(received_qty)
                    except (TypeError, ValueError):
                        return Response(
                            {"error": "received_quantity must be an integer."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if received_qty < 0:
                        return Response(
                            {"error": "received_quantity cannot be negative."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    item_id = row.get('item_id', row.get('id'))
                    product_id = row.get('product_id', row.get('product'))

                    if item_id is not None:
                        item = item_lookup.get(item_id)
                    elif product_id is not None:
                        item = product_lookup.get(product_id)
                    else:
                        return Response(
                            {"error": "Each item must include item_id (or id) or product_id (or product)."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if item is None:
                        return Response(
                            {"error": f"PO item not found for item_id={item_id} product_id={product_id}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    remaining_qty = item.quantity_ordered - item.quantity_received
                    if received_qty > remaining_qty:
                        return Response(
                            {"error": f"received_quantity {received_qty} exceeds remaining {remaining_qty} for item {item.id}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if received_qty == 0:
                        continue

                    item.quantity_received += received_qty
                    item.save(update_fields=['quantity_received'])

                    if stock_fields_available:
                        Product.objects.filter(pk=item.product_id).update(stock=F('stock') + received_qty)

                        # Create Stock Adjustment record
                        StockAdjustment.objects.create(
                            product_id=item.product_id,
                            user=request.user,
                            adjustment_type='add',
                            quantity=received_qty,
                            reason=f"Received for PO {po.po_number}",
                        )

            # Compute totals from the same in-memory list we updated to avoid stale
            # prefetched relation cache on `po.items`.
            total_ordered = sum(item.quantity_ordered for item in po_items)
            total_received = sum(item.quantity_received for item in po_items)

            if total_received == 0:
                po.status = 'Open'
            elif total_received < total_ordered:
                po.status = 'Partial'
            else:
                po.status = 'Fully Received'

            po.save(update_fields=['status'])

        return Response(
            {
                "message": "Purchase order receive processed successfully.",
                "status": po.status,
                "total_ordered_qty": total_ordered,
                "total_received_qty": total_received,
                "remaining_qty": max(total_ordered - total_received, 0),
            }
        )

class PurchaseBillViewSet(viewsets.ModelViewSet):
    queryset = PurchaseBill.objects.select_related('vendor', 'purchase_order').order_by('-created_at')
    serializer_class = PurchaseBillSerializer
    permission_classes = [IsAuthenticated]

class PurchaseReturnViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseReturn.objects
        .select_related('vendor', 'bill')
        .prefetch_related('items')
        .order_by('-created_at')
    )
    serializer_class = PurchaseReturnSerializer
    permission_classes = [IsAuthenticated]
