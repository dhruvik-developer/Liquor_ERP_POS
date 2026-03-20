from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Department, Brand, Size, Pack, TaxRate
from .serializers import (
    DepartmentSerializer, BrandSerializer, 
    SizeSerializer, PackSerializer, TaxRateSerializer
)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]

class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    permission_classes = [IsAuthenticated]

class PackViewSet(viewsets.ModelViewSet):
    queryset = Pack.objects.all()
    serializer_class = PackSerializer
    permission_classes = [IsAuthenticated]

class TaxRateViewSet(viewsets.ModelViewSet):
    queryset = TaxRate.objects.all()
    serializer_class = TaxRateSerializer
    permission_classes = [IsAuthenticated]

class LookupAllAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "departments": DepartmentSerializer(Department.objects.all(), many=True).data,
            "brands": BrandSerializer(Brand.objects.all(), many=True).data,
            "sizes": SizeSerializer(Size.objects.all(), many=True).data,
            "packs": PackSerializer(Pack.objects.all(), many=True).data,
            "tax_rates": TaxRateSerializer(TaxRate.objects.all(), many=True).data,
        })
