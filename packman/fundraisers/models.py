from django.contrib import admin
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext as _
from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from packman.calendars.models import PackYear
from packman.core.models import TimeStampedModel
from packman.membership.models import Scout


class Category(models.Model):
    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    sort_order = models.IntegerField(_("sort order"), blank=True, null=True)

    # additional legacy fields
    # qtyCase
    # qtyBox
    # qtyEachTitle

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class ProductLine(TimeStampedModel):

    name = models.CharField(_("name"), max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="product_lines", related_query_name="product_line")
    year = models.ForeignKey(PackYear, on_delete=models.CASCADE, related_name="product_lines", related_query_name="product_line", default=PackYear.get_current)

    class Meta:
        ordering = ("name", )
        verbose_name = _("Product Line")
        verbose_name_plural = _("Product Lines")

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    class WeightUnit(models.TextChoices):
        OUNCE = "OZ", _("ounce")
        POUND = "LB", _("pound")

    name = models.CharField(_("title"), max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    product_line = models.ForeignKey(ProductLine, on_delete=models.CASCADE, related_name="products", blank=True, null=True)
    price = models.DecimalField(_("price"), decimal_places=2, max_digits=9)
    weight = models.DecimalField(_("weight"), decimal_places=1, max_digits=4, blank=True, null=True)
    unit = models.CharField(_("measured in"), max_length=2, choices=WeightUnit.choices, blank=True)
    sort_order = models.IntegerField(_("sort order"), blank=True, null=True)
    year = models.ForeignKey(PackYear, on_delete=models.CASCADE, related_name="products", default=PackYear.get_current)

    # Additional legacy fields
    # csvTitle
    # mobileTitle
    # packingTitle
    # qtyCase
    # qtyBox
    # qtyTitle
    # qtyEachTitle
    # packingTableTitle

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.name


class Customer(TimeStampedModel):
    name = models.CharField(_("name"), max_length=150)

    address = models.CharField(_("address"), max_length=100, blank=True)
    city = models.CharField(_("city"), max_length=100, blank=True)
    state = USStateField(_("state"), blank=True)
    zipcode = USZipCodeField(_("ZIP code"), blank=True)
    latitude = models.FloatField(_("latitude"), blank=True, null=True)
    longitude = models.FloatField(_("longitude"), blank=True, null=True)
    gps_accuracy = models.FloatField(_("accuracy"), blank=True, null=True)

    phone_number = PhoneNumberField(_("phone number"), region="US", blank=True)

    email = models.EmailField(_("email address"), blank=True)

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    def __str__(self):
        return self.name


class Order(TimeStampedModel):

    year = models.ForeignKey(PackYear, on_delete=models.CASCADE, related_name="orders", default=PackYear.get_current)
    seller = models.ForeignKey(Scout, on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")

    donation = models.DecimalField(_("donation"), max_digits=6, decimal_places=2, blank=True, null=True)
    notes = models.TextField(_("notes"), blank=True)

    date_paid = models.DateTimeField(_("paid"), blank=True, null=True)
    date_delivered = models.DateTimeField(_("delivered"), blank=True, null=True)

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return "%s: %s" % (self.id, self.customer.name)

    @admin.display(description=_("paid"), boolean=True)
    def is_paid(self):
        return bool(self.date_paid)

    @admin.display(description=_("delivered"), boolean=True)
    def is_delivered(self):
        return bool(self.date_delivered)


class OrderItem(TimeStampedModel):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", related_query_name="item")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="orders", related_query_name="order")
    quantity = models.IntegerField(_("quantity"), validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.product.name


class Prize(TimeStampedModel):
    name = models.CharField(_("name"), max_length=100)
    points = models.IntegerField(_("points"), validators=[MinValueValidator(1)])
    value = models.DecimalField(_("retail value"), max_digits=9, decimal_places=2, blank=True, null=True)
    url = models.URLField(_("link"), blank=True)
    year = models.ForeignKey(PackYear, on_delete=models.CASCADE, related_name="prizes", default=PackYear.get_current)

    class Meta:
        ordering = ["-year", "points", "name"]
        verbose_name = _("Prize")
        verbose_name_plural = _("Prizes")

    def __str__(self):
        return self.name


class PrizeSelection(TimeStampedModel):

    year = models.ForeignKey(PackYear, on_delete=models.CASCADE, related_name="prize_selections", related_query_name="prize_selection")
    cub = models.ForeignKey(Scout, on_delete=models.CASCADE, related_name="prize_selections", related_query_name="prize_selection")
    prize = models.ForeignKey(Prize, on_delete=models.CASCADE, related_name="prize_selections", related_query_name="prize_selection")
    quantity = models.IntegerField(_("quantity"), validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _("Prize Selection")
        verbose_name_plural = _("Prize Selections")

    def __str__(self):
        return self.prize.name
