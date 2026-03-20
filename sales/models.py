from django.db import models
from usermgmt.models import TimeStampedModel, User, Store
from people.models import Customer
from inventory.models import Product
import datetime

class CashDrawerShift(TimeStampedModel):
    STATUS_CHOICES = [('Open', 'Open'), ('Closed', 'Closed')]
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    store = models.ForeignKey(Store, on_delete=models.PROTECT)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Open')

class SalesOrder(TimeStampedModel):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Completed', 'Completed'), ('Refunded', 'Refunded')]
    PAYMENT_CHOICES = [('Cash', 'Cash'), ('Card', 'Card')]
    
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    store = models.ForeignKey(Store, on_delete=models.PROTECT)
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    shift = models.ForeignKey(CashDrawerShift, on_delete=models.PROTECT)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='Cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Completed')
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            timestamp = datetime.datetime.now().strftime('%y%m%d')
            # Custom logic to grab max id and increment, abbreviated for simplicity
            self.order_number = f"SO-{timestamp}-0001"
        super().save(*args, **kwargs)

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
