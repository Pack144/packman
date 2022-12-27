from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from .models import Address, Category, PhoneNumber, Venue


class PhoneNumberInline(admin.TabularInline):
    exclude = ["member", "date_added", "published", "type"]
    extra = 0
    model = PhoneNumber


class AddressInline(admin.StackedInline):
    exclude = ["member", "date_added", "published", "type"]
    model = Address


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    inlines = [AddressInline, PhoneNumberInline]
    list_filter = ("categories",)
    list_display = ("name", "get_category_list")
    search_fields = ("name",)

    @admin.display(description=_("categories"))
    def get_category_list(self, obj):
        return ", ".join(category.name for category in obj.categories.all())


class DistributionListAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": (("name", "email"), ("is_all", "contact_us"))}),
        (_("Members"), {"fields": ("get_member_list",)}),
        (_("Selections"), {"fields": ("dens", "committees"), "classes": ("collapse",)}),
    ]
    filter_horizontal = ("committees", "dens")
    list_display = (
        "name",
        "email",
        "get_den_list",
        "get_committee_list",
        "is_all",
        "contact_us",
    )
    list_filter = ["contact_us"]
    readonly_fields = ["get_member_list"]

    @admin.display(description=_("dens"))
    def get_den_list(self, obj):
        return ", ".join(str(den.number) for den in obj.dens.all())

    @admin.display(description=_("committees"))
    def get_committee_list(self, obj):
        return ", ".join(committee.name for committee in obj.committees.all())

    @admin.display(description=_("members"))
    def get_member_list(self, obj):
        members = format_html_join(
            "",
            "<li><strong>{}</strong> <em>&lt;{}&gt;</em></li>",
            ((n, a) for n, a in obj.email_addresses),
        )
        return format_html("<ul>{}</ul>", members) if members else ""


admin.site.register(Category)
