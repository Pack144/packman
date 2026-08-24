from django.contrib import admin, messages
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from packman.calendars.models import PackYear

from .models import (
    Campaign,
    Category,
    Customer,
    Order,
    OrderItem,
    Prize,
    PrizePoint,
    PrizeSelection,
    Product,
    ProductLine,
    Quota,
    Tag,
)


class CampaignFilter(admin.SimpleListFilter):
    """
    A custom "campaign" list filter that defaults to the latest campaign
    when the changelist is first opened, instead of showing every campaign.
    """

    title = _("campaign")
    parameter_name = "campaign__id__exact"

    def lookups(self, request, model_admin):
        return [(campaign.pk, str(campaign)) for campaign in Campaign.objects.all()]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "all":
            # Explicit "All" was chosen from the filter sidebar - show everything.
            return queryset
        if value in (None, ""):
            # No filter param at all means this is the first, unfiltered load of
            # the changelist, so default to only the latest campaign instead of
            # showing every campaign's records.
            latest = Campaign.get_latest()
            return queryset.filter(campaign=latest) if latest else queryset
        return queryset.filter(campaign__pk=value)

    def choices(self, changelist):
        # Mirrors Django's default SimpleListFilter.choices(), but with two
        # deliberate differences from the stock FK filter:
        #   1. "All" links to `campaign__id__exact=all` (a sentinel value) instead
        #      of dropping the query param. That's what makes "no param" and
        #      "explicitly chose All" distinguishable in queryset() above.
        #   2. The latest campaign's choice is pre-selected when there's no query
        #      param yet, so the sidebar visually matches what queryset() did.
        latest = Campaign.get_latest()
        yield {
            "selected": self.value() == "all",
            "query_string": changelist.get_query_string({self.parameter_name: "all"}),
            "display": _("All"),
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": (self.value() is None and latest is not None and str(lookup) == str(latest.pk))
                or self.value() == str(lookup),
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }


class IsDeliveredFilter(admin.SimpleListFilter):
    title = _("delivered")
    parameter_name = "delivered"

    def lookups(self, request, model_admin):
        return ("true", _("Yes")), ("false", _("No"))

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.filter(date_delivered__isnull=False)
        if self.value() == "false":
            return queryset.filter(date_delivered__isnull=True)


class IsPaidFilter(admin.SimpleListFilter):
    title = _("paid")
    parameter_name = "paid"

    def lookups(self, request, model_admin):
        return ("true", _("Yes")), ("false", _("No"))

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.filter(date_paid__isnull=False)
        if self.value() == "false":
            return queryset.filter(date_paid__isnull=True)


class OrderInline(admin.StackedInline):
    model = Order
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PrizeSelectionInline(admin.TabularInline):
    model = PrizeSelection
    extra = 0


class QuotaInline(admin.TabularInline):
    model = Quota
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    actions = ["duplicate_campaign"]
    inlines = [QuotaInline]
    list_display = [
        "year",
        "ordering_opens",
        "ordering_closes",
        "can_take_orders",
        "delivery_available",
        "can_deliver_orders",
        "prize_window_opens",
        "prize_window_closes",
        "can_select_prizes",
    ]

    @admin.display(description=_("Duplicate campaign, quotas, and product(s)"))
    def duplicate_campaign(self, request, queryset):
        year = PackYear.objects.current()
        if queryset.count() == 1:
            original_campaign = queryset.first()
            campaign = queryset.first()
            if campaign.year == year:
                self.message_user(
                    request,
                    _("The selected Campaign is for the current Pack Year"),
                    messages.ERROR,
                )
            elif Campaign.objects.filter(year=year).exists():
                self.message_user(
                    request,
                    _("A fundraising Campaign already exists for the current Pack Year"),
                    messages.ERROR,
                )
            else:
                campaign.pk = None
                campaign.year = year
                campaign.ordering_opens = campaign.ordering_opens.replace(year=year.start_date.year)
                campaign.ordering_closes = campaign.ordering_closes.replace(year=year.start_date.year)
                campaign.delivery_available = campaign.delivery_available.replace(year=year.start_date.year)
                campaign.prize_window_opens = campaign.prize_window_opens.replace(year=year.start_date.year)
                campaign.prize_window_closes = campaign.prize_window_closes.replace(year=year.start_date.year)
                campaign.save()
                product_count = 0

                for p in original_campaign.products.all():
                    # Copy all products to the newly created campaign.
                    p.pk = None
                    p.campaign = campaign
                    p.save()
                    product_count += 1

                for q in original_campaign.quotas.all():
                    # Copy the Den quotas to the newly created campaign.
                    q.pk = None
                    q.campaign = campaign
                    q.save()

                self.message_user(
                    request,
                    ngettext(
                        f"Successfully copied {product_count} product into a new campaign for the {year} Pack Year.",
                        f"Successfully copied {product_count} products into a new campaign for the {year} Pack Year.",
                        product_count,
                    ),
                    messages.SUCCESS,
                )
        else:
            self.message_user(
                request,
                _("Please select only 1 campaign to duplicate"),
                messages.WARNING,
            )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    inlines = [OrderInline]
    list_display = ["name", "address", "city", "state", "zipcode", "phone_number", "email"]
    search_fields = ["name", "address", "phone_number", "email"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = [
        "customer",
        "seller",
        "campaign",
        "is_paid",
        "is_delivered",
        "product_total",
        "donation",
        "order_total",
    ]
    list_filter = [IsPaidFilter, IsDeliveredFilter, CampaignFilter, "seller"]

    def get_queryset(self, request):
        return super().get_queryset(request).calculate_total()

    @admin.display(description="product", ordering="subtotal")
    def product_total(self, obj):
        return obj.subtotal

    @admin.display(description="total", ordering="total")
    def order_total(self, obj):
        return obj.total


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    actions = ["duplicate_prizes"]
    list_display = ["name", "points", "value", "campaign"]
    list_filter = ["points", CampaignFilter]

    @admin.display(description=_("Copy selected prizes to the latest campaign"))
    def duplicate_prizes(self, request, queryset):
        campaign = Campaign.objects.current()
        count = 0

        for prize in queryset.all():
            if prize.campaign != campaign:
                prize.pk = None
                prize.campaign = campaign
                prize.save()
                count += 1

        self.message_user(
            request,
            ngettext(
                f"Successfully copied {count} prize for the {campaign} campaign.",
                f"Successfully copied {count} prizes for the {campaign} campaign.",
                count,
            ),
            messages.SUCCESS,
        )


@admin.register(PrizePoint)
class PrizePointAdmin(admin.ModelAdmin):
    list_display = ["value", "earned_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    actions = ["duplicate_products"]
    filter_horizontal = ["tags"]
    list_display = ["name", "category", "price", "has_description", "has_image", "campaign"]
    list_filter = ["category", "tags", CampaignFilter]

    def get_readonly_fields(self, request, obj=None):
        # Disallow changing the campaign of a product with orders.
        if obj and obj.orders.exists():
            return self.readonly_fields + ("campaign",)
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Disallow deleting a product with orders.
        if obj and obj.orders.exists():
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description=_("Copy selected products to the latest campaign"))
    def duplicate_products(self, request, queryset):
        campaign = Campaign.objects.current()
        count = 0

        for product in queryset.all():
            if product.campaign != campaign:
                product.pk = None
                product.campaign = campaign
                product.save()
                count += 1

        self.message_user(
            request,
            ngettext(
                f"Successfully copied {count} product for the {campaign} campaign.",
                f"Successfully copied {count} products for the {campaign} campaign.",
                count,
            ),
            messages.SUCCESS,
        )


@admin.register(ProductLine)
class ProductLineAdmin(admin.ModelAdmin):
    pass


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
