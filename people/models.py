from django.db import models
from usermgmt.models import TimeStampedModel

class Customer(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    loyalty_points = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Vendor(TimeStampedModel):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
