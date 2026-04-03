from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Customer, Vendor, VendorAddress, VendorTax
from .serializers import CustomerSerializer, VendorAddressSerializer, VendorSerializer, VendorTaxSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.order_by('-created_at')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['name', 'phone', 'email', 'dob', 'city', 'country']


class VendorTaxViewSet(viewsets.ModelViewSet):
    queryset = VendorTax.objects.order_by('name')
    serializer_class = VendorTaxSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['name', 'rate']


class VendorAddressViewSet(viewsets.ModelViewSet):
    queryset = VendorAddress.objects.order_by('-id')
    serializer_class = VendorAddressSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['city', 'state', 'zip', 'country', 'phone_1', 'email']


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.select_related('default_tax_class', 'address').prefetch_related('sales_contacts').order_by('-created_at')
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vendor_name', 'vendor_code', 'company_name', 'default_tax_class', 'gst_number', 'is_active']
