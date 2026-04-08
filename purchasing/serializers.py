from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseBill,
    PurchaseBillItemsDetail,
    PurchaseReturn,
    PurchaseReturnItem,
)
from people.serializers import VendorSerializer
from people.models import Vendor
from inventory.models import Product, StockAdjustment

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
        extra_kwargs = {
            'invoice_number': {
                'required': True,
                'allow_blank': False,
                'trim_whitespace': True,
            }
        }

    def validate_invoice_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Invoice number is required.")
        return value

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
        request = self.context.get('request')
        user = request.user if request else None

        with transaction.atomic():
            bill = PurchaseBill.objects.create(**validated_data)

            for item_data in items_detail:
                item = PurchaseBillItemsDetail.objects.create(purchase_bill=bill, **item_data)

                # If Direct Bill (no purchase order), update stock.
                # Use DB-side increment to avoid stale in-memory product objects
                # overwriting stock when the same product appears in multiple lines.
                if purchase_order is None:
                    quantity = item.quantity_received if item.quantity_received > 0 else item.quantity_ordered
                    if quantity > 0:
                        Product.objects.filter(pk=item.product_id).update(stock=F('stock') + quantity)

                        StockAdjustment.objects.create(
                            product_id=item.product_id,
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
    vendor_id = serializers.PrimaryKeyRelatedField(source='vendor', queryset=Vendor.objects.all())
    bill_id = serializers.PrimaryKeyRelatedField(
        source='bill',
        queryset=PurchaseBill.objects.all(),
        allow_null=True,
        required=False,
    )
    return_bill_number = serializers.CharField(required=False, allow_blank=True, validators=[])
    items = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReturn
        fields = [
            'id',
            'created_at',
            'updated_at',
            'vendor_id',
            'bill_id',
            'return_bill_number',
            'return_date',
            'bill_date',
            'due_date',
            'paid_status',
            'note',
            'other_charges',
            'total_returns',
            'sub_total',
            'total_payable',
            'items',
        ]

    def validate_return_bill_number(self, value):
        return str(value).strip()

    def _normalize_items(self, items):
        normalized_items = []
        errors = {}

        for index, item in enumerate(items):
            row_errors = {}
            product_id = item.get('product_id', item.get('product'))
            if product_id in (None, ''):
                row_errors['product_id'] = 'This field is required.'
            else:
                try:
                    product = Product.objects.get(pk=product_id)
                except Product.DoesNotExist:
                    row_errors['product_id'] = 'Invalid product.'
                else:
                    item['product'] = product

            for field in ('quantity_received', 'quantity_returned'):
                value = item.get(field, 0)
                try:
                    item[field] = int(value)
                    if item[field] < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    row_errors[field] = 'A non-negative integer is required.'

            for field in ('unit_price', 'landing_cost', 'amount'):
                value = item.get(field, 0)
                try:
                    item[field] = round(float(value), 2)
                except (TypeError, ValueError):
                    row_errors[field] = 'A valid number is required.'

            item['selected'] = bool(item.get('selected', True))
            item['sku'] = str(item.get('sku', '') or '')
            item['description'] = str(item.get('description', '') or '')

            if row_errors:
                errors[index] = row_errors
            else:
                normalized_items.append(item)

        if errors:
            raise serializers.ValidationError({'items': errors})

        return normalized_items

    @staticmethod
    def _build_item_payload(item):
        return {
            'product': item['product'],
            'sku': item.get('sku', ''),
            'description': item.get('description', ''),
            'selected': item.get('selected', True),
            'quantity_received': item.get('quantity_received', 0),
            'quantity_returned': item.get('quantity_returned', 0),
            'unit_price': item.get('unit_price', 0),
            'landing_cost': item.get('landing_cost', 0),
            'amount': item.get('amount', 0),
        }

    def _validate_stock_availability(self, items):
        requested_quantities = {}
        for item in items:
            product = item['product']
            requested_quantities[product.id] = requested_quantities.get(product.id, 0) + item.get('quantity_returned', 0)

        existing_quantities = {}
        if self.instance:
            for existing_item in self.instance.items.all():
                existing_quantities[existing_item.product_id] = (
                    existing_quantities.get(existing_item.product_id, 0) + existing_item.quantity_returned
                )

        errors = {}
        for item in items:
            product = item['product']
            requested_qty = requested_quantities[product.id]
            allowed_qty = product.stock + existing_quantities.get(product.id, 0)
            if requested_qty > allowed_qty:
                errors[str(product.id)] = (
                    f"Return quantity {requested_qty} exceeds available stock {allowed_qty} for product {product.name}."
                )

        if errors:
            raise serializers.ValidationError({'items': errors})

    def _apply_stock_delta(self, previous_items, new_items, user, return_bill_number):
        previous_quantities = {}
        for item in previous_items:
            previous_quantities[item.product_id] = previous_quantities.get(item.product_id, 0) + item.quantity_returned

        new_quantities = {}
        for item in new_items:
            product_id = item['product'].id
            new_quantities[product_id] = new_quantities.get(product_id, 0) + item.get('quantity_returned', 0)

        for product_id in set(previous_quantities) | set(new_quantities):
            previous_qty = previous_quantities.get(product_id, 0)
            new_qty = new_quantities.get(product_id, 0)
            delta = new_qty - previous_qty
            if delta == 0:
                continue

            if delta > 0:
                Product.objects.filter(pk=product_id).update(stock=F('stock') - delta)
                StockAdjustment.objects.create(
                    product_id=product_id,
                    user=user,
                    adjustment_type='reduce',
                    quantity=delta,
                    reason=f"Purchase Return {return_bill_number}",
                )
            else:
                Product.objects.filter(pk=product_id).update(stock=F('stock') + abs(delta))
                StockAdjustment.objects.create(
                    product_id=product_id,
                    user=user,
                    adjustment_type='add',
                    quantity=abs(delta),
                    reason=f"Purchase Return Update {return_bill_number}",
                )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        items = self.initial_data.get('items', serializers.empty)

        if items is serializers.empty:
            if self.instance is None:
                raise serializers.ValidationError({'items': 'This field is required.'})
            return attrs

        if not isinstance(items, list) or not items:
            raise serializers.ValidationError({'items': 'Provide at least one return item.'})

        normalized_items = self._normalize_items([dict(item) for item in items])
        self._validate_stock_availability(normalized_items)
        attrs['items'] = normalized_items

        if 'total_returns' not in attrs:
            attrs['total_returns'] = sum(item.get('quantity_returned', 0) for item in normalized_items)

        if 'sub_total' not in attrs:
            attrs['sub_total'] = round(sum(item.get('amount', 0) for item in normalized_items), 2)

        if 'total_payable' not in attrs:
            attrs['total_payable'] = round(attrs['sub_total'] + float(attrs.get('other_charges', 0)), 2)

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        user = request.user if request else None

        with transaction.atomic():
            supplied_return_bill_number = validated_data.get('return_bill_number', '')
            if not supplied_return_bill_number or PurchaseReturn.objects.filter(
                return_bill_number=supplied_return_bill_number
            ).exists():
                validated_data['return_bill_number'] = PurchaseReturn.get_next_return_bill_number()

            purchase_return = PurchaseReturn.objects.create(**validated_data)
            PurchaseReturnItem.objects.bulk_create([
                PurchaseReturnItem(
                    purchase_return=purchase_return,
                    **self._build_item_payload(item_data),
                )
                for item_data in items_data
            ])
            self._apply_stock_delta([], items_data, user, purchase_return.return_bill_number)

        return purchase_return

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', serializers.empty)
        request = self.context.get('request')
        user = request.user if request else None

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if items_data is not serializers.empty:
                previous_items = list(instance.items.all())
                instance.items.all().delete()
                PurchaseReturnItem.objects.bulk_create([
                    PurchaseReturnItem(
                        purchase_return=instance,
                        **self._build_item_payload(item_data),
                    )
                    for item_data in items_data
                ])
                self._apply_stock_delta(previous_items, items_data, user, instance.return_bill_number)

        return instance

    def get_items(self, instance):
        return [
            {
                'id': item.id,
                'product_id': item.product_id,
                'sku': item.sku,
                'description': item.description,
                'selected': item.selected,
                'quantity_received': item.quantity_received,
                'quantity_returned': item.quantity_returned,
                'unit_price': f"{item.unit_price:.2f}",
                'landing_cost': f"{item.landing_cost:.2f}",
                'amount': f"{item.amount:.2f}",
            }
            for item in instance.items.all()
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['vendor_id'] = instance.vendor_id
        data['bill_id'] = instance.bill_id
        return data
