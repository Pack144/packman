from django.contrib import admin

from .models import Category, Event, PackYear


def mark_events_cancelled(modeladmin, request, queryset):
    queryset.update(status=Event.CANCELLED)


def mark_events_confirmed(modeladmin, request, queryset):
    queryset.update(status=Event.CONFIRMED)


def mark_events_tentative(modeladmin, request, queryset):
    queryset.update(status=Event.TENTATIVE)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'icon', )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    actions = [mark_events_cancelled, mark_events_confirmed, mark_events_tentative]
    date_hierarchy = "start"
    list_display = ('name', 'get_location', 'start', 'end', 'category', 'status')
    list_filter = ('category', )
    search_fields = ('name', 'start', 'end', 'location', 'venue__name')
    readonly_fields = ('duration', )


admin.site.register(PackYear)
