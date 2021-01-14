from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Address, PhoneNumber, Venue, Category, DistributionList


class PhoneNumberInline(admin.TabularInline):
    exclude = ['member', 'date_added', 'published', 'type']
    extra = 0
    model = PhoneNumber


class AddressInline(admin.StackedInline):
    exclude = ['member', 'date_added', 'published', 'type']
    model = Address


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    inlines = [AddressInline, PhoneNumberInline]
    list_filter = ('categories', )
    list_display = ('name', "get_category_list")
    search_fields = ('name', )

    def get_category_list(self, obj):
        return ", ".join(category.name for category in obj.categories.all())

    get_category_list.short_description = _("categories")


@admin.register(DistributionList)
class DistributionListAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": (("name", "email"), ("is_all", "contact_us"))}),
        (_("Members"), {"fields": ("get_member_list", )}),
        (_("Selections"), {"fields": ("dens", "committees"), "classes": ("collapse", )}),
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

    def get_den_list(self, obj):
        return ", ".join(str(den.number) for den in obj.dens.all())

    get_den_list.short_description = _("dens")

    def get_committee_list(self, obj):
        return ", ".join(committee.name for committee in obj.committees.all())

    get_committee_list.short_description = _("committees")

    def get_member_list(self, obj):
        members = format_html_join("", "<li>{}</li>", ((mark_safe(f"<strong>{n}</strong> <em>&lt;{a}&gt;</em>"), ) for n, a in obj.email_addresses))
        return format_html("<ul>{}</ul>", members) if members else ""

    get_member_list.short_description = _("members")


admin.site.register(Category)
