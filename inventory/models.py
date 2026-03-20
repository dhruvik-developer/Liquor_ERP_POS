from django.db import models
from django.core.validators import MinValueValidator
from usermgmt.models import TimeStampedModel, User
from people.models import Vendor

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    brand = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=50)
    pack = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    stock = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

class StockAdjustment(TimeStampedModel):
    ADJUSTMENT_CHOICES = [('add', 'Add'), ('reduce', 'Reduce')]
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_CHOICES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    reason = models.CharField(max_length=100)
    note = models.TextField(null=True, blank=True)
