from django.contrib import admin

from .models import Event


class EventAdmin(admin.ModelAdmin):
    model = Event
    list_display = ('name', 'location', 'start', 'end')


admin.site.register(Event, EventAdmin)
