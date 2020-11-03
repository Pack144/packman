from django.contrib import admin

from .models import ContentBlock, Page


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 0


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    inlines = [ContentBlockInline]
    list_display = ('title', 'page', 'last_updated')
    list_display_links = ('title', 'page')
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ['title', 'published_on', ]
