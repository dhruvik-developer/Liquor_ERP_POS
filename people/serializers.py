from rest_framework import serializers
from .models import Customer, Vendor, VendorAddress, VendorTax

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class VendorTaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorTax
        fields = '__all__'


class VendorAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorAddress
        fields = '__all__'


class VendorSerializer(serializers.ModelSerializer):
    default_tax_class_name = serializers.CharField(source="default_tax_class.name", read_only=True)
    default_tax_class_rate = serializers.DecimalField(
        source="default_tax_class.rate",
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    address_details = VendorAddressSerializer(source="address", read_only=True)
    address_1 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_2 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    city = serializers.CharField(write_only=True, required=False, allow_blank=True)
    state = serializers.CharField(write_only=True, required=False, allow_blank=True)
    zip = serializers.CharField(write_only=True, required=False, allow_blank=True)
    code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    ext = serializers.CharField(write_only=True, required=False, allow_blank=True)
    country = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone_1 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone_2 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    cell_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    fax = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Vendor
        fields = [
            'id',
            'created_at',
            'updated_at',
            'vendor_name',
            'vendor_code',
            'company_name',
            'default_tax_class',
            'default_tax_class_name',
            'default_tax_class_rate',
            'pdf_format',
            'address',
            'address_details',
            'address_1',
            'address_2',
            'city',
            'state',
            'zip',
            'code',
            'ext',
            'country',
            'phone_1',
            'phone_2',
            'cell_phone',
            'fax',
            'email',
            'pay_term',
            'gst_number',
            'note',
            'is_active',
        ]
        extra_kwargs = {
            'vendor_name': {'required': True, 'allow_blank': False},
            'company_name': {'required': True, 'allow_blank': False},
        }

    ADDRESS_FIELDS = (
        "address_1",
        "address_2",
        "city",
        "state",
        "zip",
        "code",
        "ext",
        "country",
        "phone_1",
        "phone_2",
        "cell_phone",
        "fax",
        "email",
    )

    def _extract_address_payload(self, validated_data):
        payload = {}
        for field in self.ADDRESS_FIELDS:
            if field in validated_data:
                payload[field] = validated_data.pop(field)
        return payload

    @staticmethod
    def _has_non_empty_address(payload):
        return any(str(value).strip() for value in payload.values() if value is not None)

    def create(self, validated_data):
        address_payload = self._extract_address_payload(validated_data)
        vendor = super().create(validated_data)
        if address_payload and self._has_non_empty_address(address_payload):
            address_obj = VendorAddress.objects.create(**address_payload)
            vendor.address = address_obj
            vendor.save(update_fields=["address"])
        return vendor

    def update(self, instance, validated_data):
        address_payload = self._extract_address_payload(validated_data)
        vendor = super().update(instance, validated_data)

        if address_payload:
            if vendor.address:
                for field, value in address_payload.items():
                    setattr(vendor.address, field, value)
                vendor.address.save(update_fields=list(address_payload.keys()))
            elif self._has_non_empty_address(address_payload):
                address_obj = VendorAddress.objects.create(**address_payload)
                vendor.address = address_obj
                vendor.save(update_fields=["address"])

        return vendor
