from django.db import models
from django.core.validators import MinValueValidator
from usermgmt.models import TimeStampedModel
from people.models import Vendor
from inventory.models import Product

class PurchaseOrder(TimeStampedModel):
    STATUS_CHOICES = [('Open', 'Open'), ('Partial', 'Partial Received'), ('Fully Received', 'Fully Received')]
    po_number = models.CharField(max_length=50, unique=True, db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    vendor_order_ref = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    expected_date = models.DateField(null=True, blank=True)

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_ordered = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_received = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

class PurchaseBill(TimeStampedModel):
    STATUS_CHOICES = [('Draft', 'Draft'), ('Committed', 'Committed')]
    bill_number = models.CharField(max_length=100, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateTimeField()
    note = models.TextField(null=True, blank=True)

class PurchaseReturn(TimeStampedModel):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Processed', 'Processed')]
    return_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    reason = models.TextField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
