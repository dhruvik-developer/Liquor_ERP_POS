from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet,
    BrandViewSet,
    UOMViewSet,
    SizeViewSet,
    PackViewSet,
    TaxRateViewSet,
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'uoms', UOMViewSet, basename='uom')
router.register(r'sizes', SizeViewSet, basename='size')
router.register(r'packs', PackViewSet, basename='pack')
router.register(r'tax-rates', TaxRateViewSet, basename='taxrate')

urlpatterns = [
    path('', include(router.urls)),
]
