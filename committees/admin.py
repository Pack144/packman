from django.contrib import admin

from .models import Committee, Membership


class MembershipAdmin(admin.TabularInline):
    model = Membership
    classes = ['collapse']
    exclude = ['date_added']
    extra = 0


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ['name']}
    inlines = [MembershipAdmin]
