import csv
import decimal

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from packman.calendars.models import PackYear
from packman.dens.models import Membership

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
    actions = ["generate_weekly_report", "generate_campaign_report"]
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
    list_filter = [IsPaidFilter, IsDeliveredFilter, "campaign", "seller"]

    def get_queryset(self, request):
        return super().get_queryset(request).calculate_total()

    @admin.display(description="product", ordering="subtotal")
    def product_total(self, obj):
        return obj.subtotal

    @admin.display(description="total", ordering="total")
    def order_total(self, obj):
        return obj.total

    @admin.display(description=_("Generate Weekly Report"))
    def generate_weekly_report(self, request, queryset):
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=7)
        report_name = f"Campaign Weekly Report ({end_date.month}-{end_date.day}-{end_date.year}).csv"
        field_names = ["Cub", "Den", "Order Count", "Total"]

        orders = queryset.filter(date_added__gte=start_date, date_added__lte=end_date)
        members = Membership.objects.prefetch_related("scout", "den").filter(year_assigned=PackYear.objects.current())

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={report_name}"
        writer = csv.writer(response)
        writer.writerow(field_names)

        for cub in members:
            cub_orders = orders.filter(seller__den_memberships=cub)
            writer.writerow([cub.scout, cub.den, cub_orders.count(), cub_orders.totaled()["totaled"]])

        return response

    @admin.display(description=_("Generate Campaign Report"))
    def generate_campaign_report(self, request, queryset):
        campaign = Campaign.objects.current()
        report_date = timezone.now()
        orders = Order.objects.filter(campaign=campaign)
        report_name = f"Campaign Report ({report_date.month}-{report_date.day}-{report_date.year}).csv"

        field_names = [
            "Cub",
            "Den",
            "Order Count",
            "Total",
            "Quota",
            "Achieved",
            "Amount Owed",
            "Prize Points Earned",
            "Prize Points Spent",
            "Points Remaining",
        ]
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={report_name}"

        cubs = Membership.objects.prefetch_related("scout", "den", "den__quotas").filter(
            year_assigned=PackYear.objects.current(), scout__status=Membership.scout.field.related_model.ACTIVE
        )

        writer = csv.writer(response)
        writer.writerow(field_names)
        for cub in cubs:
            cub_orders = orders.filter(seller__den_memberships=cub)
            total = cub_orders.totaled()["totaled"]
            quota = cub.den.quotas.current().target

            # calculate points earned
            if total < quota:
                points_earned = 0
            elif total <= 2000:
                points_earned = PrizePoint.objects.filter(earned_at__lte=total).order_by("-earned_at").first().value
            else:
                points_earned = PrizePoint.objects.order_by("earned_at").last().value + int(
                    (total - PrizePoint.objects.order_by("earned_at").last().earned_at) / 100
                )

            points_spent = PrizeSelection.objects.filter(
                cub=cub.scout, campaign=campaign
            ).calculate_total_points_spent()["spent"]
            points_remaining = points_earned - points_spent

            # TODO: Don't hard-code the minimum if quota unmet
            met_quota = total >= quota
            if not met_quota:
                shortfall = quota - total
                owed = total + shortfall * decimal.Decimal("0.65")
            else:
                owed = total
            writer.writerow(
                [
                    cub.scout,
                    cub.den,
                    cub_orders.count(),
                    total,
                    quota,
                    met_quota,
                    owed.quantize(decimal.Decimal(".01")),
                    points_earned,
                    points_spent,
                    points_remaining,
                ]
            )
        return response


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    actions = ["duplicate_prizes"]
    list_display = ["name", "points", "value", "campaign"]
    list_filter = ["points", "campaign"]

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
    list_filter = ["category", "tags", "campaign"]

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
