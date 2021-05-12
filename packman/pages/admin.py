from django.contrib import admin

from .forms import ContentBlockForm, PageForm
from .models import ContentBlock, Page, Image


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 0
    form = ContentBlockForm


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageForm
    inlines = [ContentBlockInline]
    list_display = ("title", "page", "last_updated")
    list_display_links = ("title", "page")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = [
        "title",
        "published_on",
    ]


admin.site.register(Image)
