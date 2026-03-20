from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet, BrandViewSet, SizeViewSet,
    PackViewSet, TaxRateViewSet, LookupAllAPIView
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'sizes', SizeViewSet, basename='size')
router.register(r'packs', PackViewSet, basename='pack')
router.register(r'tax-rates', TaxRateViewSet, basename='taxrate')

urlpatterns = [
    path('all/', LookupAllAPIView.as_view(), name='lookups-all'),
    path('', include(router.urls)),
]
