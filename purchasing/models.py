from django.db import models
from django.core.validators import MinValueValidator
from usermgmt.models import TimeStampedModel
from people.models import Vendor
from inventory.models import Product

class PurchaseOrder(TimeStampedModel):
    STATUS_CHOICES = [('Open', 'Open'), ('Partial', 'Partial Received'), ('Fully Received', 'Fully Received')]
    po_number = models.CharField(max_length=50, unique=True, db_index=True)
    po_id = models.CharField(max_length=100, blank=True, default="")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    vendor_order_ref = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(blank=True, default="")
    ship_to = models.CharField(max_length=255, blank=True, default="")
    ship_by = models.CharField(max_length=255, blank=True, default="")
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
    bill_number = models.CharField(max_length=100, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL)
    sales_person = models.CharField(max_length=255, blank=True, default="")
    bill_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_1 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_2 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_3 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    deposit_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    return_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    overhead = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateTimeField()
    note = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last_bill_numbers = (
                PurchaseBill.objects
                .exclude(bill_number='')
                .order_by('-id')
                .values_list('bill_number', flat=True)
            )
            next_seq = 1
            for number in last_bill_numbers:
                if str(number).isdigit():
                    next_seq = int(number) + 1
                    break

            self.bill_number = str(next_seq)
            while PurchaseBill.objects.filter(bill_number=self.bill_number).exists():
                next_seq += 1
                self.bill_number = str(next_seq)

        super().save(*args, **kwargs)

class PurchaseBillItemsDetail(models.Model):
    purchase_bill = models.ForeignKey(PurchaseBill, related_name='items_detail', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_ordered = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_received = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

class PurchaseReturn(TimeStampedModel):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Processed', 'Processed')]
    return_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    reason = models.TextField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
