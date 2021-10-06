from django.contrib import admin
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
