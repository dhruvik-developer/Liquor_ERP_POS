from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Customer, Vendor
from .serializers import CustomerSerializer, VendorSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.order_by('-created_at')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['name', 'phone', 'email']

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.order_by('-created_at')
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['name', 'phone']
