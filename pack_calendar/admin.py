from django.contrib import admin

from .models import Category, Event


class CategoryAdmin(admin.ModelAdmin):
    model = Category
    list_display = ('name', 'color', 'icon', )


class EventAdmin(admin.ModelAdmin):
    model = Event
    list_display = ('name', 'get_location', 'start', 'category', )
    list_filter = ('category', )


admin.site.register(Event, EventAdmin)
admin.site.register(Category, CategoryAdmin)
