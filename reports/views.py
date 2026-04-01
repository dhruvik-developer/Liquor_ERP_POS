from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, DecimalField, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Product
from sales.models import SalesOrder, SalesOrderItem
from usermgmt.drf_auth import JWTAuthentication

from .serializers import DashboardResponseSerializer


class DashboardAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    PERIOD_DAYS = 30
    TOP_SELLING_LIMIT = 5
    ALERT_LIMIT = 10

    @staticmethod
    def _to_money(value):
        amount = Decimal(value or 0)
        return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _to_percentage(value):
        amount = Decimal(value or 0)
        return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _to_decimal(value):
        if value is None:
            return Decimal("0")
        try:
            text = str(value).strip()
            if text == "":
                return Decimal("0")
            return Decimal(text)
        except Exception:
            return Decimal("0")

    @staticmethod
    def _percentage_change(current_value, previous_value):
        current = Decimal(current_value or 0)
        previous = Decimal(previous_value or 0)

        if previous == 0:
            if current == 0:
                return Decimal("0")
            return Decimal("100")

        return ((current - previous) / previous) * Decimal("100")

    def _build_metric(self, current_value, previous_value, value_serializer):
        change = self._percentage_change(current_value, previous_value)
        return {
            "value": value_serializer(current_value),
            "change": self._to_percentage(change),
            "is_positive": change >= 0,
        }

    @staticmethod
    def _alert_status(stock, threshold):
        critical_threshold = max(1, threshold // 2)
        return "critical" if stock <= critical_threshold else "low"

    def get(self, request):
        period_end = timezone.now()
        period_start = period_end - timedelta(days=self.PERIOD_DAYS)
        previous_start = period_start - timedelta(days=self.PERIOD_DAYS)

        money_zero = Value(Decimal("0.00"), output_field=DecimalField(max_digits=18, decimal_places=2))
        count_zero = Value(0, output_field=IntegerField())

        completed_orders = SalesOrder.objects.filter(status="Completed")

        current_order_stats = completed_orders.filter(
            created_at__gte=period_start,
            created_at__lt=period_end,
        ).aggregate(
            revenue=Coalesce(Sum("total_amount"), money_zero),
            transactions=Coalesce(Count("id"), count_zero),
        )

        previous_order_stats = completed_orders.filter(
            created_at__gte=previous_start,
            created_at__lt=period_start,
        ).aggregate(
            revenue=Coalesce(Sum("total_amount"), money_zero),
            transactions=Coalesce(Count("id"), count_zero),
        )

        completed_items = SalesOrderItem.objects.filter(order__status="Completed").select_related(
            "order",
            "product",
            "product__cost_pricing",
        )

        def calculate_cost(window_start, window_end):
            total_cost = Decimal("0")
            window_items = completed_items.filter(
                order__created_at__gte=window_start,
                order__created_at__lt=window_end,
            )
            for item in window_items:
                unit_cost = self._to_decimal(getattr(getattr(item.product, "cost_pricing", None), "unit_cost", "0"))
                total_cost += Decimal(item.quantity or 0) * unit_cost
            return total_cost

        current_cost = calculate_cost(period_start, period_end)
        previous_cost = calculate_cost(previous_start, period_start)

        current_revenue = Decimal(current_order_stats["revenue"] or 0)
        previous_revenue = Decimal(previous_order_stats["revenue"] or 0)
        current_transactions = int(current_order_stats["transactions"] or 0)
        previous_transactions = int(previous_order_stats["transactions"] or 0)

        current_profit = current_revenue - Decimal(current_cost or 0)
        previous_profit = previous_revenue - Decimal(previous_cost or 0)

        current_avg_order_value = current_revenue / current_transactions if current_transactions else Decimal("0")
        previous_avg_order_value = previous_revenue / previous_transactions if previous_transactions else Decimal("0")

        top_selling_queryset = completed_items.filter(
            order__created_at__gte=period_start,
            order__created_at__lt=period_end,
        ).values(
            "product__name",
            "product__image_base64",
        ).annotate(
            sold=Coalesce(Sum("quantity"), count_zero),
            revenue=Coalesce(Sum("subtotal"), money_zero),
        ).order_by("-sold", "-revenue")[: self.TOP_SELLING_LIMIT]

        top_selling = [
            {
                "name": row["product__name"],
                "sold": row["sold"],
                "revenue": self._to_money(row["revenue"]),
                "image": row["product__image_base64"],
            }
            for row in top_selling_queryset
        ]

        product_stock_queryset = Product.objects.select_related("stock_information").annotate(
            total_added=Coalesce(
                Sum("stockadjustment__quantity", filter=Q(stockadjustment__adjustment_type="add")),
                0,
            ),
            total_reduced=Coalesce(
                Sum("stockadjustment__quantity", filter=Q(stockadjustment__adjustment_type="reduce")),
                0,
            ),
        )

        alerts = []
        for product in product_stock_queryset:
            stock_left = int((product.total_added or 0) - (product.total_reduced or 0))
            warn_qty = int(self._to_decimal(getattr(getattr(product, "stock_information", None), "min_warn_qty", "0")))
            if warn_qty > 0 and stock_left < warn_qty:
                alerts.append(
                    {
                        "name": product.name,
                        "sku": product.sku,
                        "stock_left": max(0, stock_left),
                        "status": self._alert_status(stock_left, warn_qty),
                    }
                )

        alerts = sorted(alerts, key=lambda item: (item["stock_left"], item["name"]))[: self.ALERT_LIMIT]

        response_payload = {
            "status": True,
            "message": "Dashboard data fetched successfully",
            "data": {
                "total_revenue": self._build_metric(current_revenue, previous_revenue, self._to_money),
                "profit": self._build_metric(current_profit, previous_profit, self._to_money),
                "transactions": self._build_metric(current_transactions, previous_transactions, int),
                "avg_order_value": self._build_metric(current_avg_order_value, previous_avg_order_value, self._to_money),
                "top_selling": top_selling,
                "alerts": alerts,
            },
        }

        serializer = DashboardResponseSerializer(data=response_payload)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)
