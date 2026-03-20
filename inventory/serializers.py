from rest_framework import serializers
from .models import Category, Product, StockAdjustment

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    total_value = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

    def get_total_value(self, obj):
        return obj.stock * obj.price

class StockAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAdjustment
        fields = '__all__'
        read_only_fields = ['user']
