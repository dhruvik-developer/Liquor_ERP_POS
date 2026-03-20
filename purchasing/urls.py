from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseOrderViewSet, PurchaseBillViewSet, PurchaseReturnViewSet

router = DefaultRouter()
router.register(r'orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'bills', PurchaseBillViewSet, basename='purchasebill')
router.register(r'returns', PurchaseReturnViewSet, basename='purchasereturn')

urlpatterns = [
    path('', include(router.urls)),
]
