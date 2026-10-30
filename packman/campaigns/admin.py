from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import DropdownFilter
from unfold.widgets import UnfoldBooleanWidget

from packman.calendars.models import PackYear
from packman.membership.models import Scout

from .models import (
    Campaign,
    CampaignScout,
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


def filter_by_campaign_selection(queryset, value):
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


class CampaignFilter(DropdownFilter):
    """
    A custom "campaign" list filter that defaults to the latest campaign
    when the changelist is first opened, instead of showing every campaign.
    """

    title = _("campaign")
    parameter_name = "campaign__id__exact"
    all_option = ("all", _("All"))

    def lookups(self, request, model_admin):
        return [(campaign.pk, str(campaign)) for campaign in Campaign.objects.all()]

    def queryset(self, request, queryset):
        try:
            return filter_by_campaign_selection(queryset, self.value())
        except (ValueError, ValidationError) as e:
            raise IncorrectLookupParameters(e) from e

    def choices(self, changelist):
        latest = Campaign.get_latest()
        for choice in super().choices(changelist):
            if self.value() in (None, "") and latest is not None:
                choice["form"].data = {self.parameter_name: str(latest.pk)}
            yield choice


class SellerFilter(DropdownFilter):
    """
    A searchable "seller" list filter offering only the Cubs with orders in
    the campaign selected by CampaignFilter.
    """

    title = _("seller")
    parameter_name = "seller__id__exact"

    def lookups(self, request, model_admin):
        orders = model_admin.get_queryset(request)
        try:
            campaign_orders = filter_by_campaign_selection(orders, request.GET.get(CampaignFilter.parameter_name))
            sellers = Q(pk__in=campaign_orders.values("seller"))
            if self.value():
                # Keep the active seller visible after switching campaigns.
                sellers |= Q(pk=Scout._meta.pk.to_python(self.value()))
        except (ValueError, ValidationError) as e:
            raise IncorrectLookupParameters(e) from e
        return [
            (scout.pk, str(scout))
            for scout in Scout.objects.filter(sellers, pk__in=orders.values("seller")).order_by(
                "last_name", "nickname", "first_name"
            )
        ]

    def has_output(self):
        # Django skips filters without choices; keep an active seller value applied.
        return bool(self.value()) or super().has_output()

    def queryset(self, request, queryset):
        if self.value():
            try:
                return queryset.filter(seller__pk=Scout._meta.pk.to_python(self.value()))
            except ValidationError as e:
                raise IncorrectLookupParameters(e) from e
        return queryset


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


class OrderAdminForm(forms.ModelForm):
    award_ineligible = forms.BooleanField(
        label=_("Award Ineligible"),
        required=False,
        help_text=Order._meta.get_field("award_ineligible").help_text,
        widget=UnfoldBooleanWidget,
    )

    class Meta:
        model = Order
        fields = "__all__"

    def clean_award_ineligible(self):
        return True if self.cleaned_data["award_ineligible"] else None


class OrderInline(StackedInline):
    model = Order
    extra = 0


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0


class PrizeSelectionInline(TabularInline):
    model = PrizeSelection
    extra = 0


class QuotaInline(TabularInline):
    model = Quota
    extra = 0


class CampaignScoutInline(TabularInline):
    model = CampaignScout
    template_before = "admin/campaigns/campaign/scout_guidance.html"
    autocomplete_fields = ("scout",)
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(ModelAdmin):
    actions = ["duplicate_campaign"]
    change_form_before_template = "admin/campaigns/campaign/form_guidance.html"
    change_list_template = "admin/change_list_with_guidance.html"
    list_guidance_template = "admin/campaigns/campaign/list_guidance.html"
    inlines = [QuotaInline, CampaignScoutInline]
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

    @admin.action(description=_("Duplicate campaign, quotas, and products"))
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
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "description"]


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    inlines = [OrderInline]
    list_display = ["name", "address", "city", "state", "zipcode", "phone_number", "email"]
    search_fields = ["name", "address", "phone_number", "email"]


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_filter_submit = True
    form = OrderAdminForm
    inlines = [OrderItemInline]
    list_display = [
        "customer",
        "seller",
        "campaign",
        "is_paid",
        "is_delivered",
        "is_award_ineligible",
        "product_total",
        "donation",
        "order_total",
    ]
    list_filter = [IsPaidFilter, IsDeliveredFilter, "award_ineligible", CampaignFilter, SellerFilter]
    search_fields = [
        "seller__first_name",
        "seller__nickname",
        "seller__last_name",
        "customer__name",
        "customer__email",
        "customer__phone_number",
        "customer__address",
    ]
    search_help_text = _("Search by seller name or customer name, email, phone number, or address.")

    def get_queryset(self, request):
        return super().get_queryset(request).calculate_total()

    @admin.display(description="product", ordering="subtotal")
    def product_total(self, obj):
        return obj.subtotal

    @admin.display(description="total", ordering="total")
    def order_total(self, obj):
        return obj.total

    @admin.display(description=_("Award Ineligible"), boolean=True, ordering="award_ineligible")
    def is_award_ineligible(self, obj):
        return obj.award_ineligible is True


@admin.register(Prize)
class PrizeAdmin(ModelAdmin):
    list_filter_submit = True
    actions = ["duplicate_prizes"]
    list_display = ["name", "points", "value", "campaign"]
    list_filter = ["points", CampaignFilter]

    @admin.display(description=_("Copy selected prizes to the latest campaign"))
    def duplicate_prizes(self, request, queryset):
        campaign = Campaign.objects.latest()
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
class PrizePointAdmin(ModelAdmin):
    change_list_template = "admin/change_list_with_guidance.html"
    list_guidance_template = "admin/campaigns/prizepoint/list_guidance.html"
    list_display = ["value", "earned_at"]


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_filter_submit = True
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
        campaign = Campaign.objects.latest()
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
class ProductLineAdmin(ModelAdmin):
    pass


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    pass
