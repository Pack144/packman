from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Content, DynamicPage, StaticPage


class CategoryInline(admin.TabularInline):
    model = DynamicPage.categories.through
    extra = 0
    verbose_name = _("Category")
    verbose_name_plural = _("Categories")


class ContentInline(admin.StackedInline):
    model = Content
    extra = 0
    verbose_name = _("Content Section")
    verbose_name_plural = _("Content")

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'page')
    list_display_links = ('__str__', )


@admin.register(DynamicPage)
class DynamicPageAdmin(admin.ModelAdmin):
    exclude = ['categories', ]
    inlines = [CategoryInline, ContentInline]
    list_display = ('title', 'last_updated', )
    list_filter = ('categories', )
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ['title', 'categories', 'published_on', ]


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ('page', 'title', 'last_updated')
    list_display_links = ('page', 'title')
    inlines = [ContentInline]


admin.site.register(Category)
