from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Attachment, Category, DynamicPage, StaticPage


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


class CategoryInline(admin.TabularInline):
    model = DynamicPage.categories.through
    extra = 0
    verbose_name = _('Category')
    verbose_name_plural = _('Categories')


class DynamicPageAdmin(admin.ModelAdmin):
    exclude = ['categories', ]
    inlines = [AttachmentInline, CategoryInline]
    list_display = ('title', 'published_on', 'last_updated', )
    list_filter = ('categories', )
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ['title', 'categories', 'published_on', ]


class StaticPageAdmin(admin.ModelAdmin):
    inlines = [AttachmentInline, ]


admin.site.register(Attachment)
admin.site.register(Category)
admin.site.register(DynamicPage, DynamicPageAdmin)
admin.site.register(StaticPage, StaticPageAdmin)
