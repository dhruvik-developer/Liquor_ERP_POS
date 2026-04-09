from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CashDrawerShiftViewSet, SalesOrderViewSet, SalesReturnViewSet

router = DefaultRouter()
router.register(r'shifts', CashDrawerShiftViewSet, basename='shift')
router.register(r'orders', SalesOrderViewSet, basename='salesorder')
router.register(r'return', SalesReturnViewSet, basename='salesreturn')

urlpatterns = [
    path('', include(router.urls)),
]
