from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from inventory.models import Product, StockAdjustment
from .models import (
    CashDrawerShift,
    SalesOrder,
    SalesOrderItem,
    SalesReturn,
    SalesReturnItem,
)

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


class SalesReturnItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(source='product', queryset=Product.objects.all())
    order_item_id = serializers.PrimaryKeyRelatedField(
        source='order_item',
        queryset=SalesOrderItem.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = SalesReturnItem
        fields = ['id', 'product_id', 'order_item_id', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['id']


class SalesReturnSerializer(serializers.ModelSerializer):
    order_id = serializers.PrimaryKeyRelatedField(source='order', queryset=SalesOrder.objects.all())
    items = SalesReturnItemSerializer(many=True)

    class Meta:
        model = SalesReturn
        fields = [
            'id',
            'created_at',
            'updated_at',
            'return_number',
            'order_id',
            'store',
            'cashier',
            'customer',
            'reason',
            'status',
            'subtotal',
            'tax_amount',
            'discount_amount',
            'total_amount',
            'items',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'return_number', 'cashier']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        order = attrs.get('order') or getattr(self.instance, 'order', None)
        items = attrs.get('items', None)

        if not order:
            raise serializers.ValidationError({'order_id': 'Order is required.'})
        if not items:
            raise serializers.ValidationError({'items': 'At least one return item is required.'})

        # Ensure return belongs to same store as the original order.
        store = attrs.get('store') or getattr(self.instance, 'store', None)
        if store and order.store_id != store.id:
            raise serializers.ValidationError({'store': 'Store must match the sales order store.'})

        sold_qty_by_order_item = {}
        sold_qty_by_product = {}
        for item in order.items.all():
            sold_qty_by_order_item[item.id] = item.quantity
            sold_qty_by_product[item.product_id] = sold_qty_by_product.get(item.product_id, 0) + item.quantity

        existing_returned_order_item = {}
        existing_returned_product = {}
        existing_returns = SalesReturnItem.objects.filter(sales_return__order=order)
        if self.instance:
            existing_returns = existing_returns.exclude(sales_return=self.instance)
        for item in existing_returns:
            if item.order_item_id:
                existing_returned_order_item[item.order_item_id] = (
                    existing_returned_order_item.get(item.order_item_id, 0) + item.quantity
                )
            existing_returned_product[item.product_id] = (
                existing_returned_product.get(item.product_id, 0) + item.quantity
            )

        cumulative_requested_order_item = {}
        cumulative_requested_product = {}
        errors = {}

        for index, item in enumerate(items):
            product = item['product']
            quantity = item['quantity']
            order_item = item.get('order_item')
            subtotal = item.get('subtotal')
            unit_price = item.get('unit_price')

            row_errors = {}
            if quantity <= 0:
                row_errors['quantity'] = 'Quantity must be greater than zero.'

            # Optional guard: subtotal should align with unit_price * quantity.
            expected_subtotal = (Decimal(quantity) * unit_price).quantize(Decimal('0.01'))
            if subtotal != expected_subtotal:
                row_errors['subtotal'] = 'Subtotal must equal quantity * unit_price.'

            if order_item:
                if order_item.order_id != order.id:
                    row_errors['order_item_id'] = 'Order item does not belong to the given sales order.'
                elif order_item.product_id != product.id:
                    row_errors['product_id'] = 'Product does not match selected order item.'

                cumulative_requested_order_item[order_item.id] = (
                    cumulative_requested_order_item.get(order_item.id, 0) + quantity
                )
            else:
                cumulative_requested_product[product.id] = cumulative_requested_product.get(product.id, 0) + quantity

            if row_errors:
                errors[index] = row_errors

        if errors:
            raise serializers.ValidationError({'items': errors})

        # Validate requested quantities against originally sold quantities.
        for order_item_id, requested_qty in cumulative_requested_order_item.items():
            sold_qty = sold_qty_by_order_item.get(order_item_id, 0)
            already_returned = existing_returned_order_item.get(order_item_id, 0)
            if requested_qty + already_returned > sold_qty:
                raise serializers.ValidationError({
                    'items': f'Return quantity {requested_qty} exceeds sold quantity for order item {order_item_id}.'
                })

        for product_id, requested_qty in cumulative_requested_product.items():
            sold_qty = sold_qty_by_product.get(product_id, 0)
            already_returned = existing_returned_product.get(product_id, 0)
            if requested_qty + already_returned > sold_qty:
                raise serializers.ValidationError({
                    'items': f'Return quantity {requested_qty} exceeds sold quantity for product {product_id}.'
                })

        if attrs.get('customer') is None:
            attrs['customer'] = order.customer
        if attrs.get('store') is None:
            attrs['store'] = order.store

        calc_subtotal = sum((item['subtotal'] for item in items), Decimal('0.00'))
        calc_tax = attrs.get('tax_amount', Decimal('0.00'))
        calc_discount = attrs.get('discount_amount', Decimal('0.00'))
        calc_total = attrs.get('total_amount', Decimal('0.00'))
        if calc_total != (calc_subtotal + calc_tax - calc_discount):
            raise serializers.ValidationError({
                'total_amount': 'Total must equal subtotal + tax_amount - discount_amount.'
            })

        attrs['subtotal'] = calc_subtotal
        return attrs

    @staticmethod
    def _update_stock(previous_items, new_items, user, return_number):
        previous_qty = {}
        for item in previous_items:
            previous_qty[item.product_id] = previous_qty.get(item.product_id, 0) + item.quantity

        new_qty = {}
        for item in new_items:
            product_id = item['product'].id
            new_qty[product_id] = new_qty.get(product_id, 0) + item['quantity']

        for product_id in set(previous_qty) | set(new_qty):
            delta = new_qty.get(product_id, 0) - previous_qty.get(product_id, 0)
            if delta == 0:
                continue
            Product.objects.filter(pk=product_id).update(stock=F('stock') + delta)
            StockAdjustment.objects.create(
                product_id=product_id,
                user=user,
                adjustment_type='add' if delta > 0 else 'reduce',
                quantity=abs(delta),
                reason=f"Sales Return {return_number}",
            )

    @staticmethod
    def _sync_order_status(order):
        sold_total = sum(item.quantity for item in order.items.all())
        returned_total = sum(item.quantity for item in SalesReturnItem.objects.filter(sales_return__order=order))
        if sold_total > 0 and sold_total == returned_total:
            if order.status != 'Refunded':
                order.status = 'Refunded'
                order.save(update_fields=['status'])
        elif order.status == 'Refunded':
            order.status = 'Completed'
            order.save(update_fields=['status'])

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        user = request.user if request else None

        with transaction.atomic():
            sales_return = SalesReturn.objects.create(**validated_data)
            SalesReturnItem.objects.bulk_create([
                SalesReturnItem(
                    sales_return=sales_return,
                    product=item['product'],
                    order_item=item.get('order_item'),
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    subtotal=item['subtotal'],
                )
                for item in items_data
            ])
            self._update_stock([], items_data, user, sales_return.return_number)
            self._sync_order_status(sales_return.order)

        return sales_return

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        request = self.context.get('request')
        user = request.user if request else None

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if items_data is not None:
                previous_items = list(instance.items.all())
                instance.items.all().delete()
                SalesReturnItem.objects.bulk_create([
                    SalesReturnItem(
                        sales_return=instance,
                        product=item['product'],
                        order_item=item.get('order_item'),
                        quantity=item['quantity'],
                        unit_price=item['unit_price'],
                        subtotal=item['subtotal'],
                    )
                    for item in items_data
                ])
                self._update_stock(previous_items, items_data, user, instance.return_number)
                self._sync_order_status(instance.order)

        return instance
