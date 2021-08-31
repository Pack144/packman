from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext as _

from .models import Committee, CommitteeMember


class CommitteeMemberAdmin(admin.TabularInline):
    autocomplete_fields = ["member"]
    model = CommitteeMember
    exclude = ["date_added"]
    extra = 0


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": (("name", "slug"), "description")}),
        (_("Permissions"), {"fields": (("are_staff", "are_superusers"), "permissions"), "classes": ("collapse",)}),
    )
    filter_horizontal = ("permissions",)
    inlines = [CommitteeMemberAdmin]
    list_display = ["name", "description", "leadership", "are_staff", "are_superusers"]
    list_filter = ["committee_member__year", "leadership", "are_staff", "are_superusers"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = (
        "name",
        "description",
        "membership__den__number",
        "members__first_name",
        "members__nickname",
        "members__last_name",
    )


# This application does not rely on Dango groups; we'll assign permissions to Committee instead.
# Remove the groups section from Admin to avoid confusion.
admin.site.unregister(Group)
