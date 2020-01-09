from django.contrib import admin

from .models import Address, PhoneNumber, Venue, VenueType


class PhoneNumberInline(admin.TabularInline):
    exclude = ['member', 'date_added', 'published', 'type']
    extra = 0
    model = PhoneNumber


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    inlines = [PhoneNumberInline]
    list_filter = ('type', )
    list_display = ('name',)
    search_fields = ('name', )


admin.site.register(Address)
admin.site.register(VenueType)
