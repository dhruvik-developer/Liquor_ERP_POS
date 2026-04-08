from rest_framework import serializers
from .models import Department, Brand, UOM, Size, Pack, TaxRate

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class UOMSerializer(serializers.ModelSerializer):
    class Meta:
        model = UOM
        fields = '__all__'


class SizeSerializer(serializers.ModelSerializer):
    uom_name = serializers.CharField(source='uom.name', read_only=True)
    unit_price_uom_name = serializers.CharField(source='unit_price_uom.name', read_only=True)

    class Meta:
        model = Size
        fields = [
            'id',
            'name',
            'localized_name',
            'uom',
            'uom_name',
            'no_of_units',
            'units_in_case',
            'tax_factor',
            'unit_price_factor',
            'unit_price_uom',
            'unit_price_uom_name',
        ]

class PackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pack
        fields = '__all__'

class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = '__all__'
