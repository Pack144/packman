from django.contrib import admin

from .models import Committee, Membership


class MembershipAdmin(admin.TabularInline):
    autocomplete_fields = ['member']
    model = Membership
    exclude = ['date_added']
    extra = 0


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['name']}
    inlines = [MembershipAdmin]
    list_display = ['name', 'description', 'leadership']
    list_filter = ['membership__year_served', 'leadership']
    search_fields = ('name', 'description', 'membership__den')
