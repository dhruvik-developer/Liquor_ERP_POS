from django.contrib import admin
from .models import Customer, Vendor, VendorAddress, VendorSalesContact, VendorTax

admin.site.register(Customer)
admin.site.register(VendorTax)
admin.site.register(VendorAddress)
admin.site.register(Vendor)
admin.site.register(VendorSalesContact)
