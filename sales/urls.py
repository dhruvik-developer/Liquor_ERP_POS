from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CashDrawerShiftViewSet, SalesOrderViewSet

router = DefaultRouter()
router.register(r'shifts', CashDrawerShiftViewSet, basename='shift')
router.register(r'orders', SalesOrderViewSet, basename='salesorder')

urlpatterns = [
    path('', include(router.urls)),
]
