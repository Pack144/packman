from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, DynamicPage, StaticPage


class CategoryInline(admin.TabularInline):
    model = DynamicPage.categories.through
    extra = 0
    verbose_name = _('Category')
    verbose_name_plural = _('Categories')


class DynamicPageAdmin(admin.ModelAdmin):
    exclude = ['categories', ]
    inlines = [CategoryInline]
    list_display = ('title', 'published_on', 'last_updated', )
    list_filter = ('categories', )
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ['title', 'categories', 'published_on', ]


admin.site.register(Category)
admin.site.register(DynamicPage, DynamicPageAdmin)
admin.site.register(StaticPage)
