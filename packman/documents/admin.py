from django.contrib import admin

from .models import Category, Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    model = Document
    list_display = (
        "name",
        "category",
        "last_updated",
    )
    list_filter = ("category",)
    readonly_fields = (
        "date_added",
        "last_updated",
    )


admin.site.register(Category)
