from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F
from sales.models import SalesOrder
from inventory.models import Product

class DashboardStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_sales = SalesOrder.objects.filter(status='Completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        low_stock_count = Product.objects.filter(stock__lte=F('low_stock_threshold')).count()

        return Response({
            "total_sales": total_sales,
            "low_stock_items": low_stock_count,
            "gross_profit": "0.00" # Add dynamic calculation later based on item cost array
        })
