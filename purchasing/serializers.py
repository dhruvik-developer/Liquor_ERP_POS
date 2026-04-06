from rest_framework import serializers
from .models import PurchaseOrder, PurchaseOrderItem, PurchaseBill, PurchaseBillItemsDetail, PurchaseReturn
from people.serializers import VendorSerializer
from inventory.models import StockAdjustment

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        read_only_fields = ['purchase_order']

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    vendor_details = VendorSerializer(source='vendor', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        po = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=po, **item_data)
        return po

class PurchaseBillItemsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseBillItemsDetail
        fields = '__all__'
        read_only_fields = ['purchase_bill']

class PurchaseBillSerializer(serializers.ModelSerializer):
    items_detail = PurchaseBillItemsDetailSerializer(many=True, required=False)

    class Meta:
        model = PurchaseBill
        fields = '__all__'
        read_only_fields = ['bill_number']

    def validate(self, attrs):
        purchase_order = attrs.get('purchase_order')
        items_detail = attrs.get('items_detail')

        if self.instance:
            purchase_order = attrs.get('purchase_order', self.instance.purchase_order)
            has_existing_items = self.instance.items_detail.exists()
        else:
            has_existing_items = False

        if purchase_order is None and not items_detail and not has_existing_items:
            raise serializers.ValidationError({
                "items_detail": "This field is required when purchase_order is blank."
            })

        return attrs

    def create(self, validated_data):
        items_detail = validated_data.pop('items_detail', [])
        purchase_order = validated_data.get('purchase_order')
        bill = PurchaseBill.objects.create(**validated_data)
        
        request = self.context.get('request')
        user = request.user if request else None

        for item_data in items_detail:
            item = PurchaseBillItemsDetail.objects.create(purchase_bill=bill, **item_data)
            
            # If Direct Bill (no purchase order), update stock
            if purchase_order is None:
                quantity = item.quantity_received if item.quantity_received > 0 else item.quantity_ordered
                if quantity > 0:
                    product = item.product
                    if hasattr(product, 'stock'):
                        product.stock += quantity
                        product.save(update_fields=['stock'])
                        
                        # Create Stock Adjustment record
                        StockAdjustment.objects.create(
                            product=product,
                            user=user,
                            adjustment_type='add',
                            quantity=quantity,
                            reason=f"Direct Bill {bill.bill_number}",
                        )
        return bill

    def update(self, instance, validated_data):
        items_detail = validated_data.pop('items_detail', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_detail is not None:
            instance.items_detail.all().delete()
            for item_data in items_detail:
                PurchaseBillItemsDetail.objects.create(purchase_bill=instance, **item_data)

        return instance

class PurchaseReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseReturn
        fields = '__all__'
