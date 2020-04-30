from django.contrib import admin

from .models import GroupMailbox


@admin.register(GroupMailbox)
class GroupMailboxAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email')
