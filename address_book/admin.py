from django.contrib import admin

from .models import Address, PhoneNumber, Venue, VenueType


class VenueAdmin(admin.ModelAdmin):
    model = Venue
    list_filter = ('type', )
    list_display = ('name', 'type',)


admin.site.register(Venue, VenueAdmin)
admin.site.register(VenueType)
admin.site.register(Address)
admin.site.register(PhoneNumber)
