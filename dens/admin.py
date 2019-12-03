from django.contrib import admin

from .models import Den, Rank


class DenAdmin(admin.ModelAdmin):
    list_display = ('number', 'rank', )
    list_filter = ('rank', )


admin.site.register(Den, DenAdmin)
admin.site.register(Rank)
