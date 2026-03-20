from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, StockAdjustmentViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'adjustments', StockAdjustmentViewSet, basename='stockadjustment')

urlpatterns = [
    path('', include(router.urls)),
]
