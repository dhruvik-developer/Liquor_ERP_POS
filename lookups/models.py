from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    localized_name = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=150, blank=True, default="")

    def __str__(self):
        return self.name


class UOM(models.Model):
    name = models.CharField(max_length=50, unique=True)
    localized_name = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=50, unique=True)
    localized_name = models.CharField(max_length=100, blank=True, default="")
    category = models.ForeignKey(
        "inventory.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sizes",
    )
    uom = models.ForeignKey(
        "lookups.UOM",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sizes",
    )

    def __str__(self):
        return self.name


class Pack(models.Model):
    name = models.CharField(max_length=50, unique=True)
    localized_name = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.name

class TaxRate(models.Model):
    name = models.CharField(max_length=50)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"
