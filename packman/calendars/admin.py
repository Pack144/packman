from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .models import Category, Event, PackYear


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "color",
        "icon",
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    actions = ["mark_cancelled", "mark_confirmed", "mark_tentative"]
    date_hierarchy = "start"
    list_display = ("name", "get_location", "start", "end", "category", "status")
    list_filter = ("category", "status", "start")
    search_fields = ("name", "start", "end", "location", "venue__name")
    readonly_fields = ("duration",)

    def mark_cancelled(self, request, queryset):
        updates = queryset.update(status=Event.CANCELLED)
        self.message_user(
            request,
            ngettext(
                "%d event was successfully cancelled.",
                "%d events were successfully cancelled.",
                updates,
            )
            % updates,
            messages.WARNING,
        )

    mark_cancelled.short_description = _("Cancel selected events")
    mark_cancelled.allowed_permissions = ("change",)

    def mark_confirmed(self, request, queryset):
        updates = queryset.update(status=Event.CONFIRMED)
        self.message_user(
            request,
            ngettext(
                "%d event was successfully confirmed.",
                "%d events were successfully confirmed.",
                updates,
            )
            % updates,
            messages.SUCCESS,
        )

    mark_confirmed.short_description = _("Confirm selected events")
    mark_confirmed.allowed_permissions = ("change",)

    def mark_tentative(self, request, queryset):
        updates = queryset.update(status=Event.TENTATIVE)
        self.message_user(
            request,
            ngettext(
                "%d event was successfully marked as tentative.",
                "%d events were successfully marked as tentative.",
                updates,
            )
            % updates,
            messages.INFO,
        )

    mark_tentative.short_description = _("Mark selected events as tentative")
    mark_tentative.allowed_permissions = ("change",)


@admin.register(PackYear)
class PackYearManager(admin.ModelAdmin):
    list_display = ("year", "start_date", "end_date")
