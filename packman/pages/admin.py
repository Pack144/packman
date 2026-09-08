from django.contrib import admin

from adminsortable2.admin import SortableAdminBase, SortableAdminMixin, SortableInlineAdminMixin

from .forms import PageForm
from .models import ContentBlock, Page


class ContentBlockInline(SortableInlineAdminMixin, admin.StackedInline):
    model = ContentBlock
    extra = 0
    prepopulated_fields = {"bookmark": ("heading",)}
    radio_fields = {"visibility": admin.HORIZONTAL}


@admin.register(Page)
class PageAdmin(SortableAdminMixin, SortableAdminBase, admin.ModelAdmin):
    form = PageForm
    inlines = [ContentBlockInline]
    list_display = ("title", "nav_placement", "last_updated")
    list_display_links = ("title",)
    list_filter = ("nav_placement",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = [
        "title",
        "slug",
        "content_blocks__heading",
        "content_blocks__body",
    ]
