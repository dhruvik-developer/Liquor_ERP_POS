from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Prefetch
from .models import Category, SubCategory, Product, StockAdjustment, Promotion, CardSetup
from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
    ProductSerializer,
    StockAdjustmentSerializer,
    PromotionSerializer,
    CardSetupSerializer,
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.select_related('category', 'category__department').all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related(
        'department',
        'category',
        'sub_category',
        'brand',
        'size',
        'pack',
        'tax_rate',
        'cost_pricing',
        'stock_information',
    ).prefetch_related(
        Prefetch(
            'stockadjustment_set',
            queryset=StockAdjustment.objects.select_related('user').order_by('-created_at'),
            to_attr='prefetched_stock_adjustments',
        )
    ).all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = [
        'department',
        'category',
        'sub_category',
        'brand',
        'size',
        'pack',
        'tax_rate',
        'item_is_inactive',
        'non_taxable',
        'buy_as_case',
        'non_discountable',
    ]

class StockAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = StockAdjustment.objects.all()
    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            adjustment = serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]


class CardSetupViewSet(viewsets.ModelViewSet):
    queryset = CardSetup.objects.all()
    serializer_class = CardSetupSerializer
    permission_classes = [IsAuthenticated]
