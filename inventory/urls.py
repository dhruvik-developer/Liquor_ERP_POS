from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, SubCategoryViewSet, ProductViewSet, StockAdjustmentViewSet, PromotionViewSet, CardSetupViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'sub-categories', SubCategoryViewSet, basename='subcategory')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'adjustments', StockAdjustmentViewSet, basename='stockadjustment')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'card-setups', CardSetupViewSet, basename='cardsetup')

urlpatterns = [
    path('', include(router.urls)),
]
