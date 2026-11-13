from django.contrib import admin

from tinymce.models import HTMLField
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin, StackedInline

from .forms import PageForm, PageOrderFormSet
from .models import ContentBlock, Page


class ContentBlockInline(StackedInline):
    formfield_overrides = {HTMLField: {"widget": TinyMCE}}
    model = ContentBlock
    extra = 0
    prepopulated_fields = {"bookmark": ("heading",)}
    radio_fields = {"visibility": admin.HORIZONTAL}
    ordering_field = "order"
    hide_ordering_field = True


@admin.register(Page)
class PageAdmin(ModelAdmin):
    ordering_field = "order"
    hide_ordering_field = True
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

    def get_changelist_formset(self, request, **kwargs):
        class ScopedPageOrderFormSet(PageOrderFormSet):
            ordering_queryset = self.get_queryset(request)

        return super().get_changelist_formset(request, formset=ScopedPageOrderFormSet, **kwargs)

    def save_model(self, request, obj, form, change):
        # Django's list-editable path saves individual forms instead of calling formset.save().
        if pages := getattr(obj, "_normalized_page_orders", None):
            self.get_queryset(request).bulk_update(pages, ["order"])
        super().save_model(request, obj, form, change)
