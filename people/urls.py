from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, VendorAddressViewSet, VendorTaxViewSet, VendorViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'vendor-taxes', VendorTaxViewSet, basename='vendor-tax')
router.register(r'vendor-addresses', VendorAddressViewSet, basename='vendor-address')
router.register(r'vendors', VendorViewSet, basename='vendor')

urlpatterns = [
    path('', include(router.urls)),
]
