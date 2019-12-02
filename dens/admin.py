from django.contrib import admin

from .models import Den


class DenAdmin(admin.ModelAdmin):
    list_display = ('number', 'rank', 'category', )
    list_filter = ('rank', )


admin.site.register(Den, DenAdmin)
