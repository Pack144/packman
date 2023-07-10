from django.contrib import admin

from .forms import PageForm
from .models import ContentBlock, Page


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 0
    prepopulated_fields = {"bookmark": ("heading",)}
    radio_fields = {"visibility": admin.HORIZONTAL}


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageForm
    inlines = [ContentBlockInline]
    list_display = ("title", "page", "last_updated")
    list_display_links = ("title", "page")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = [
        "title",
        "slug",
        "content_blocks__heading",
        "content_blocks__body",
    ]
