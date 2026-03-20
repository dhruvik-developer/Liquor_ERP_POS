from rest_framework import serializers
from .models import CashDrawerShift, SalesOrder, SalesOrderItem

class CashDrawerShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashDrawerShift
        fields = '__all__'

class SalesOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderItem
        fields = '__all__'
        read_only_fields = ['order']

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True)

    class Meta:
        model = SalesOrder
        fields = '__all__'
        read_only_fields = ['order_number', 'cashier']

    def validate(self, data):
        subtotal = data.get('subtotal', 0)
        tax = data.get('tax_amount', 0)
        discount = data.get('discount_amount', 0)
        total = data.get('total_amount', 0)

        # Cross check calculation
        if abs(subtotal + tax - discount - total) > 0.01:
            raise serializers.ValidationError("Math mismatch. Total must equal Subtotal + Tax - Discount.")

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = SalesOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            SalesOrderItem.objects.create(order=order, **item_data)
            
        return order
