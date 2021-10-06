import decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from packman.calendars.models import PackYear
from packman.core.models import TimeStampedModel, TimeStampedUUIDModel
from packman.dens.models import Den
from packman.membership.models import Scout

from .managers import CampaignQuerySet, OrderItemQuerySet, OrderQuerySet, ProductQuerySet, QuotaQuerySet


def latest_campaign():
    return {"campaign": Campaign.get_latest()}


class Campaign(TimeStampedModel):
    """
    A simple model tracking the status of an individual fundraising campaign.
    """

    year = models.ForeignKey(
        PackYear, on_delete=models.CASCADE, related_name="campaigns", default=PackYear.get_current_id
    )

    ordering_opens = models.DateField(_("sales open"), help_text=_("The date when members can start taking orders."))
    ordering_closes = models.DateField(
        _("sales close"), help_text=_("The final date when all orders must be submitted.")
    )
    delivery_available = models.DateField(
        _("delivery available"), help_text=_("The date when orders will be available to be delivered.")
    )
    prize_window_opens = models.DateField(
        _("prize selection open"), help_text=_("The date when members can start selecting prizes.")
    )
    prize_window_closes = models.DateField(
        _("prize selection close"), help_text=_("The final date when members can make prize selections.")
    )
    dens = models.ManyToManyField(Den, through="Quota", related_name="campaigns", blank=True)

    objects = CampaignQuerySet.as_manager()

    class Meta:
        get_latest_by = "ordering_opens"
        ordering = ("-ordering_opens",)
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def __str__(self):
        return str(self.year)

    def clean(self):
        if self.ordering_closes < self.ordering_opens:
            raise ValidationError(
                {"ordering_closes": _("Ordering window cannot close before it opens.")}, code="invalid"
            )
        if self.prize_window_closes < self.prize_window_opens:
            raise ValidationError(
                {"prize_window_closes": _("Prize selection window cannot close before it opens.")}, code="invalid"
            )
        if self.delivery_available < self.ordering_opens:
            raise ValidationError(
                {"delivery_available": _("Orders cannot be delivered prior to taking orders.")}, code="invalid"
            )

    @admin.display(boolean=True, description=_("orders open"))
    def can_take_orders(self):
        return bool(self.ordering_opens <= timezone.now().date() <= self.ordering_closes)

    @admin.display(boolean=True, description=_("prizes open"))
    def can_select_prizes(self):
        return bool(self.prize_window_opens <= timezone.now().date() <= self.prize_window_closes)

    @admin.display(boolean=True, description=_("delivery available"))
    def can_deliver_orders(self):
        return bool(self.delivery_available <= timezone.now().date())

    @classmethod
    def get_latest(cls):
        try:
            return cls.objects.latest()
        except cls.DoesNotExist:
            pass


class Quota(models.Model):
    """
    A simple intermediate through model tracking quotas for individual Dens.
    """

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    den = models.ForeignKey(Den, on_delete=models.CASCADE, related_name="quotas")
    target = models.DecimalField(_("quota"), max_digits=6, decimal_places=2)

    objects = QuotaQuerySet.as_manager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=("campaign", "den"), name="unique_quota_per_campaign")]
        get_latest_by = "campaign"

    def __str__(self):
        return str(self.den)


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


class Tag(models.Model):
    name = models.CharField(_("name"), max_length=100)

    class Meta:
        ordering = ("name",)
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.name


class ProductLine(TimeStampedModel):
    """
    A simple model representing a line of related products.
    """

    name = models.CharField(_("name"), max_length=100)

    class Meta:
        ordering = ("name",)
        verbose_name = _("Product Line")
        verbose_name_plural = _("Product Lines")

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    """
    A simple model representing a product offered for sale during a
    fundraising campaign.
    """

    class WeightUnit(models.TextChoices):
        OUNCE = "OZ", _("ounce")
        POUND = "LB", _("pound")

    name = models.CharField(_("title"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    tags = models.ManyToManyField(Tag, related_name="products", blank=True)
    image = models.ImageField(_("image"), upload_to="campaigns/", blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    product_line = models.ForeignKey(
        ProductLine, on_delete=models.CASCADE, related_name="products", blank=True, null=True
    )
    msrp = models.DecimalField(_("MSRP"), decimal_places=2, max_digits=9, blank=True, null=True)
    price = models.DecimalField(_("sell price"), decimal_places=2, max_digits=9, blank=True, null=True)
    cost = models.DecimalField(_("wholesale cost"), decimal_places=2, max_digits=9, blank=True, null=True)
    weight = models.DecimalField(_("weight"), decimal_places=1, max_digits=4, blank=True, null=True)
    unit = models.CharField(_("measured in"), max_length=2, choices=WeightUnit.choices, blank=True)
    sort_order = models.IntegerField(_("sort order"), blank=True, null=True)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="products", default=Campaign.get_latest
    )

    # Additional legacy fields
    # csvTitle
    # mobileTitle
    # packingTitle
    # qtyCase
    # qtyBox
    # qtyTitle
    # qtyEachTitle
    # packingTableTitle

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("category", "sort_order", "name")
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.name

    def savings(self):
        return self.msrp - self.price

    def margin(self):
        return self.price - self.cost

    @admin.display(boolean=True, description=_("description"))
    def has_description(self):
        return bool(self.description)

    @admin.display(boolean=True, description=_("image"))
    def has_image(self):
        return bool(self.image)


class PrizePoint(models.Model):
    """
    A simple model representing the points that can be earned through product
    sales as an incentive. Points can be spent on prizes offered during the
    campaign.
    """

    earned_at = models.DecimalField(_("earned at"), max_digits=6, decimal_places=2)
    value = models.IntegerField(_("point value"))

    class Meta:
        ordering = ("earned_at",)
        verbose_name = _("Prize Point")
        verbose_name_plural = _("Prize Points")

    def __str__(self):
        return str(self.value)


class Customer(TimeStampedUUIDModel):
    """
    A model representing the customer of a sale.
    """

    name = models.CharField(_("name"), max_length=150, help_text=_("The name to place on the order"))

    address = models.CharField(_("address"), max_length=100, blank=True)
    city = models.CharField(_("city"), max_length=100, blank=True)
    state = USStateField(_("state"), blank=True)
    zipcode = USZipCodeField(_("ZIP code"), blank=True)
    latitude = models.FloatField(_("latitude"), blank=True, null=True)
    longitude = models.FloatField(_("longitude"), blank=True, null=True)
    gps_accuracy = models.FloatField(_("accuracy"), blank=True, null=True)

    phone_number = PhoneNumberField(
        _("phone number"),
        region="US",
        blank=True,
        help_text=_("We would use this only if we needed to talk to you about your order."),
    )

    email = models.EmailField(
        _("email address"),
        blank=True,
        help_text=_(
            "If provided, we will email you a receipt for this order. We do not share this information with anyone, including BSA."
        ),
    )

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    def __str__(self):
        return self.name

    def get_address_display(self):
        address_components = (
            self.address.strip(),
            self.city.strip(),
            self.state.strip(),
            self.zipcode.strip(),
        )
        return ", ".join(filter(None, address_components))


class Order(TimeStampedUUIDModel):
    """
    A model representing a sale.
    """

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="orders", default=Campaign.get_latest
    )
    seller = models.ForeignKey(Scout, on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders", blank=True, null=True)

    donation = models.DecimalField(
        _("donation"),
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Would you care to make monetary donation to the Pack?"),
    )
    notes = models.TextField(
        _("notes"),
        blank=True,
        help_text=_('''Use the notes field to keep reminders such as "It's okay to leave nuts in the milkbox"'''),
    )

    date_paid = models.DateTimeField(_("paid"), blank=True, null=True)
    date_delivered = models.DateTimeField(_("delivered"), blank=True, null=True)

    objects = OrderQuerySet.as_manager()

    class Meta:
        ordering = ("-date_added",)
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return "%s: %s" % (self.date_added.date(), self.customer or "unknown")

    def get_absolute_url(self):
        return reverse("campaigns:order_detail", args=[self.pk])

    def annotated_items(self):
        """Create an aggregated queryset"""
        return self.items.all().aggregate(
            total=Coalesce(
                Sum(F("product__price") * F("quantity"), output_field=models.DecimalField()), decimal.Decimal(0.00)
            ),
            count=Coalesce(Sum("quantity"), 0),
        )

    @admin.display(description=_("paid"), boolean=True)
    def is_paid(self):
        return bool(self.date_paid)

    @admin.display(description=_("delivered"), boolean=True)
    def is_delivered(self):
        return bool(self.date_delivered)

    def get_total(self):
        if self.donation:
            return self.annotated_items()["total"] + self.donation
        else:
            return self.annotated_items()["total"]

    def product_count(self):
        return self.annotated_items()["count"]


class OrderItem(TimeStampedModel):
    """
    An intermediate model binding the sale of a product to an order.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", related_query_name="item")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="orders",
        related_query_name="order",
        limit_choices_to=latest_campaign,
    )
    quantity = models.IntegerField(_("quantity"), default=1, validators=[MinValueValidator(1)])

    objects = OrderItemQuerySet.as_manager()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return _("%s (%s)") % (self.product.name, self.quantity)

    def get_total_item_price(self):
        return self.quantity * self.product.price


class Prize(TimeStampedModel):
    """
    A simple model representing a prize that may be selected by redeeming
    points earned through sales.
    """

    name = models.CharField(_("name"), max_length=150)
    points = models.IntegerField(_("points"), validators=[MinValueValidator(1)])
    value = models.DecimalField(_("retail value"), max_digits=9, decimal_places=2, blank=True, null=True)
    url = models.URLField(_("link"), max_length=320, blank=True)
    image = models.ImageField(_("image"), upload_to="campaigns/", blank=True)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="prizes", default=Campaign.get_latest
    )

    class Meta:
        ordering = ["-campaign", "points", "name"]
        verbose_name = _("Prize")
        verbose_name_plural = _("Prizes")

    def __str__(self):
        return self.name


class PrizeSelection(TimeStampedModel):

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="prize_selections",
        related_query_name="prize_selection",
        default=Campaign.get_latest,
    )
    cub = models.ForeignKey(
        Scout, on_delete=models.CASCADE, related_name="prize_selections", related_query_name="prize_selection"
    )
    prize = models.ForeignKey(
        Prize,
        on_delete=models.CASCADE,
        related_name="prize_selections",
        related_query_name="prize_selection",
        limit_choices_to=latest_campaign,
    )
    quantity = models.IntegerField(_("quantity"), validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _("Prize Selection")
        verbose_name_plural = _("Prize Selections")

    def __str__(self):
        return self.prize.name
