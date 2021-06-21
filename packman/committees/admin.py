from django.contrib import admin
from django.utils.translation import gettext as _

from .models import Committee, Membership


class MembershipAdmin(admin.TabularInline):
    autocomplete_fields = ["member"]
    model = Membership
    exclude = ["date_added"]
    extra = 0


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": (("name", "slug"), "description")}),
        (_("Permissions"), {"fields": (("are_staff", "are_superusers"), "permissions"), "classes": ("collapse",)}),
    )
    filter_horizontal = ("permissions",)
    inlines = [MembershipAdmin]
    list_display = ["name", "description", "leadership", "are_staff", "are_superusers"]
    list_filter = ["membership__year_served", "leadership", "are_staff", "are_superusers"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ("name", "description", "membership__den__number", "members__first_name", "members__nickname", "members__last_name")
