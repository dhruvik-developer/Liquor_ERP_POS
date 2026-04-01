from django.db import models
from django.core.validators import MinValueValidator
from usermgmt.models import TimeStampedModel, User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    localized_name = models.CharField(max_length=100, blank=True, default="")
    department = models.ForeignKey(
        "lookups.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
    )

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    localized_name = models.CharField(max_length=100, blank=True, default="")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_categories",
    )

    class Meta:
        unique_together = ("name", "category")

    def __str__(self):
        return self.name


class CostPricing(models.Model):
    unit_cost = models.CharField(max_length=50, blank=True, default="")
    margin = models.CharField(max_length=50, blank=True, default="")
    buydown = models.CharField(max_length=50, blank=True, default="")
    markup = models.CharField(max_length=50, blank=True, default="")
    unit_price = models.CharField(max_length=50, blank=True, default="")
    msrp = models.CharField(max_length=50, blank=True, default="")
    min_price = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"CostPricing<{self.id}>"


class StockInformation(models.Model):
    enter_upcs = models.TextField(blank=True, default="")
    min_warn_qty = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"StockInfo<{self.id}>"


class Promotion(TimeStampedModel):
    title = models.CharField(max_length=255)
    tagline = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    image_base64 = models.TextField(blank=True, default="")
    status = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CardSetup(TimeStampedModel):
    name = models.CharField(max_length=150)
    fee = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    department = models.ForeignKey(
        "lookups.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    sub_category = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    brand = models.ForeignKey(
        "lookups.Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    size = models.ForeignKey(
        "lookups.Size",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    pack = models.ForeignKey(
        "lookups.Pack",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    non_taxable = models.BooleanField(default=False)
    tax_rate = models.ForeignKey(
        "lookups.TaxRate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    cost_pricing = models.OneToOneField(
        CostPricing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product",
    )
    stock_information = models.OneToOneField(
        StockInformation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product",
    )
    item_is_inactive = models.BooleanField(default=False)
    buy_as_case = models.BooleanField(default=False)
    units_in_case = models.CharField(max_length=50, blank=True, default="")
    case_cost = models.CharField(max_length=50, blank=True, default="")
    case_price = models.CharField(max_length=50, blank=True, default="")
    non_discountable = models.BooleanField(default=False)
    image_base64 = models.TextField(blank=True, default="")

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
