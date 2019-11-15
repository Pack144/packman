from django.contrib import admin

from .models import Category, Event


class EventAdmin(admin.ModelAdmin):
    model = Event
    list_display = ('name', 'get_location', 'start', 'category', )
    list_filter = ('category', )


admin.site.register(Event, EventAdmin)
admin.site.register(Category)
