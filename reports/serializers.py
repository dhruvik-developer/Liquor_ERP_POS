from rest_framework import serializers


class DashboardMetricSerializer(serializers.Serializer):
    value = serializers.FloatField()
    change = serializers.FloatField()
    is_positive = serializers.BooleanField()


class TopSellingProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    sold = serializers.IntegerField(min_value=0)
    revenue = serializers.FloatField()
    image = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class LowStockAlertSerializer(serializers.Serializer):
    name = serializers.CharField()
    sku = serializers.CharField()
    stock_left = serializers.IntegerField(min_value=0)
    status = serializers.ChoiceField(choices=["low", "critical"])


class DashboardDataSerializer(serializers.Serializer):
    total_revenue = DashboardMetricSerializer()
    profit = DashboardMetricSerializer()
    transactions = DashboardMetricSerializer()
    avg_order_value = DashboardMetricSerializer()
    top_selling = TopSellingProductSerializer(many=True)
    alerts = LowStockAlertSerializer(many=True)


class DashboardResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    message = serializers.CharField()
    data = DashboardDataSerializer()
