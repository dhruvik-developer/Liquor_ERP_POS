from rest_framework import serializers
from .models import Category, SubCategory, Product, StockAdjustment, CostPricing, StockInformation, Promotion, CardSetup
import base64
import uuid
import binascii
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import mimetypes
from django.core.files.base import ContentFile

class Base64ImageField(serializers.ImageField):
    MAX_IMAGE_BYTES = 5 * 1024 * 1024

    def _build_content_file_from_url(self, image_url: str):
        try:
            request = Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=10) as response:
                content_type = response.headers.get_content_type()
                if not content_type or not content_type.startswith("image/"):
                    raise serializers.ValidationError("Provided image URL is not a valid image.")

                raw_bytes = response.read(self.MAX_IMAGE_BYTES + 1)
                if len(raw_bytes) > self.MAX_IMAGE_BYTES:
                    raise serializers.ValidationError("Image is too large. Max allowed size is 5MB.")
        except URLError:
            raise serializers.ValidationError("Could not fetch image from URL.")

        parsed_url = urlparse(image_url)
        extension = mimetypes.guess_extension(content_type)
        if not extension:
            extension = parsed_url.path.rsplit(".", 1)[-1] if "." in parsed_url.path else "jpg"
            extension = extension if str(extension).startswith(".") else f".{extension}"
        return ContentFile(raw_bytes, name=f"{uuid.uuid4()}{extension}")

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.strip()
            if data == "":
                return None
            if data.startswith('data:image'):
                try:
                    format, imgstr = data.split(';base64,')
                    ext = format.split('/')[-1]
                    data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                except (ValueError, binascii.Error):
                    raise serializers.ValidationError("Invalid base64 image data.")
            elif data.startswith("http://") or data.startswith("https://"):
                data = self._build_content_file_from_url(data)
        return super().to_internal_value(data)

class CategorySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'localized_name', 'department', 'department_name']


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_department_name = serializers.CharField(source='category.department.name', read_only=True)
    sub_category = serializers.CharField(source='name', read_only=True)
    category_display = serializers.SerializerMethodField()

    def get_category_display(self, obj):
        category_name = getattr(obj.category, "name", "") if obj.category else ""
        department_name = (
            getattr(obj.category.department, "name", "")
            if obj.category and obj.category.department
            else ""
        )
        if category_name and department_name:
            return f"{category_name} -> {department_name}"
        return category_name or department_name or ""

    class Meta:
        model = SubCategory
        fields = [
            'id',
            'name',
            'sub_category',
            'localized_name',
            'category',
            'category_name',
            'category_department_name',
            'category_display',
        ]


class CostPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostPricing
        fields = [
            'id',
            'unit_cost',
            'margin',
            'buydown',
            'markup',
            'unit_price',
            'msrp',
            'min_price',
        ]
        read_only_fields = ['id']


class StockInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockInformation
        fields = ['id', 'enter_upcs', 'min_warn_qty']
        read_only_fields = ['id']


class ProductSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    size_name = serializers.CharField(source='size.name', read_only=True)
    pack_name = serializers.CharField(source='pack.name', read_only=True)
    tax_rate_name = serializers.CharField(source='tax_rate.name', read_only=True)
    cost_pricing = CostPricingSerializer(required=False, allow_null=True)
    stock_information = StockInformationSerializer(required=False, allow_null=True)
    image = Base64ImageField(required=False, allow_null=True)
    total_stock_available = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def validate(self, attrs):
        department = attrs.get('department') or getattr(self.instance, 'department', None)
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        sub_category = attrs.get('sub_category') or getattr(self.instance, 'sub_category', None)
        size = attrs.get('size') or getattr(self.instance, 'size', None)
        non_taxable = attrs.get('non_taxable')
        if non_taxable is None and self.instance:
            non_taxable = self.instance.non_taxable
        if non_taxable is None:
            non_taxable = False

        if department and category and category.department_id and category.department_id != department.id:
            raise serializers.ValidationError({"category": "Selected category does not belong to selected department."})

        if category and sub_category and sub_category.category_id and sub_category.category_id != category.id:
            raise serializers.ValidationError({"sub_category": "Selected sub-category does not belong to selected category."})

        if non_taxable:
            attrs['tax_rate'] = None

        return attrs

    def _upsert_cost_pricing(self, instance, payload):
        if payload is None:
            instance.cost_pricing = None
            return

        cost_pricing_obj = getattr(instance, "cost_pricing", None)
        if cost_pricing_obj:
            for key, value in payload.items():
                setattr(cost_pricing_obj, key, value)
            cost_pricing_obj.save()
        else:
            cost_pricing_obj = CostPricing.objects.create(**payload)
        instance.cost_pricing = cost_pricing_obj

    def _upsert_stock_information(self, instance, payload):
        if payload is None:
            instance.stock_information = None
            return

        stock_information_obj = getattr(instance, "stock_information", None)
        if stock_information_obj:
            for key, value in payload.items():
                setattr(stock_information_obj, key, value)
            stock_information_obj.save()
        else:
            stock_information_obj = StockInformation.objects.create(**payload)
        instance.stock_information = stock_information_obj

    def create(self, validated_data):
        cost_pricing_payload = validated_data.pop("cost_pricing", serializers.empty)
        stock_information_payload = validated_data.pop("stock_information", serializers.empty)
        product = Product.objects.create(**validated_data)

        if cost_pricing_payload is not serializers.empty:
            self._upsert_cost_pricing(product, cost_pricing_payload)

        if stock_information_payload is not serializers.empty:
            self._upsert_stock_information(product, stock_information_payload)

        if cost_pricing_payload is not serializers.empty or stock_information_payload is not serializers.empty:
            product.save(update_fields=["cost_pricing", "stock_information"])

        return product

    def update(self, instance, validated_data):
        cost_pricing_payload = validated_data.pop("cost_pricing", serializers.empty)
        stock_information_payload = validated_data.pop("stock_information", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        fields_to_update = list(validated_data.keys())

        if cost_pricing_payload is not serializers.empty:
            self._upsert_cost_pricing(instance, cost_pricing_payload)
            fields_to_update.append("cost_pricing")

        if stock_information_payload is not serializers.empty:
            self._upsert_stock_information(instance, stock_information_payload)
            fields_to_update.append("stock_information")

        if fields_to_update:
            instance.save(update_fields=list(set(fields_to_update)))

        return instance

    def _get_adjustments(self, obj):
        adjustments = getattr(obj, "prefetched_stock_adjustments", None)
        if adjustments is None:
            adjustments = obj.stockadjustment_set.select_related('user').order_by('-created_at')
        return adjustments

    def get_total_stock_available(self, obj):
        return obj.stock

class StockAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAdjustment
        fields = '__all__'
        read_only_fields = ['user']


class PromotionSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)
    class Meta:
        model = Promotion
        fields = '__all__'


class CardSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardSetup
        fields = '__all__'
