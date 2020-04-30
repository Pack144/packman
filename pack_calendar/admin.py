from django.contrib import admin

from .models import AttendeeGroup, Category, Event, PackYear


@admin.register(AttendeeGroup)
class AttendeeGroupAdmin(admin.ModelAdmin):
    search_fields = ('group',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'icon', )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    autocomplete_fields = ('attendees', 'attendee_groups')
    list_display = ('name', 'get_location', 'start', 'end', 'category', )
    list_filter = ('category', )
    search_fields = ('name', 'start', 'end', 'location', 'venue__name')
    readonly_fields = ('duration', )


admin.site.register(PackYear)
