import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _

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
from packman.calendars.models import PackYear
from packman.dens.models import Membership


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
    actions = ["generate_weekly_report"]
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
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={report_name}"

        orders = queryset.filter(date_added__gte=start_date, date_added__lte=end_date)
        members = Membership.objects.prefetch_related("scout", "den").filter(year_assigned=PackYear.objects.current())

        writer = csv.writer(response)
        writer.writerow(field_names)
        for cub in members:
            cub_orders = orders.filter(seller__den_memberships=cub)
            writer.writerow([cub.scout, cub.den, cub_orders.count(), cub_orders.totaled()["totaled"]])

        return response


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ["name", "points", "value", "campaign"]
    list_filter = ["points", "campaign"]


@admin.register(PrizePoint)
class PrizePointAdmin(admin.ModelAdmin):
    list_display = ["value", "earned_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    filter_horizontal = ["tags"]
    list_display = ["name", "category", "price", "has_description", "has_image", "campaign"]
    list_filter = ["category", "tags", "campaign"]


@admin.register(ProductLine)
class ProductLineAdmin(admin.ModelAdmin):
    pass


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
