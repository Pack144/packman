from django.contrib import admin

from address_book.models import Address
from .models import Event


class AddressInline(admin.StackedInline):
    model = Address
    extra = 0


class EventAdmin(admin.ModelAdmin):
    model = Event
    list_display = ('name', 'location', 'start', 'end', )
    list_filter = ('category', )
    inlines = (AddressInline, )


admin.site.register(Event, EventAdmin)
