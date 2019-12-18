from django.contrib import admin

from .models import Address, PhoneNumber, Venue, VenueType


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_filter = ('type', )
    list_display = ('name', 'type',)
    search_fields = ('name', )


admin.site.register(VenueType)
admin.site.register(Address)
admin.site.register(PhoneNumber)
