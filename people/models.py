from django.db import models
from usermgmt.models import TimeStampedModel

class Customer(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    dob = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.name


class VendorTax(models.Model):
    name = models.CharField(max_length=50)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class VendorAddress(models.Model):
    address_1 = models.CharField(max_length=255, blank=True, default="")
    address_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip = models.CharField(max_length=20, blank=True, default="")
    code = models.CharField(max_length=50, blank=True, default="")
    ext = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    phone_1 = models.CharField(max_length=20, blank=True, default="")
    phone_2 = models.CharField(max_length=20, blank=True, default="")
    cell_phone = models.CharField(max_length=20, blank=True, default="")
    fax = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    def __str__(self):
        parts = [self.address_1, self.city, self.state]
        return ", ".join([part for part in parts if part]) or f"VendorAddress {self.id}"


class Vendor(TimeStampedModel):
    vendor_name = models.CharField(max_length=255, default="")
    vendor_code = models.CharField(max_length=100, blank=True, default="")
    company_name = models.CharField(max_length=255, default="")
    default_tax_class = models.ForeignKey(
        VendorTax,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendors",
    )
    pdf_format = models.CharField(max_length=100, blank=True, default="")
    address = models.ForeignKey(
        VendorAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendors",
    )
    pay_term = models.CharField(max_length=100, blank=True, default="")
    gst_number = models.CharField(max_length=100, blank=True, default="")
    note = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.vendor_name
