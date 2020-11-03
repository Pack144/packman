from django.contrib import admin

from .models import Category, ContentBlock, DynamicPage, StaticPage


class CategoryInline(admin.TabularInline):
    model = DynamicPage.categories.through
    extra = 0


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 0


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'page')
    list_display_links = ('__str__', )
    list_filter = ('page',)
    search_fields = ['title', 'body']


@admin.register(DynamicPage)
class DynamicPageAdmin(admin.ModelAdmin):
    exclude = ['categories', ]
    inlines = [CategoryInline, ContentBlockInline]
    list_display = ('title', 'last_updated', )
    list_filter = ('categories', )
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ['title', 'categories', 'published_on', ]


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ('page', 'title', 'last_updated')
    list_display_links = ('page', 'title')
    inlines = [ContentBlockInline]


admin.site.register(Category)
