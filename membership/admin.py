from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .forms import AccountCreationForm, AccountChangeForm
from .models import Account, Parent, Scout, Family


class ParentAdmin(admin.ModelAdmin):
    model = Parent
    list_display = ('short_name', 'last_name', 'email', 'status')
    list_display_links = ['short_name', 'last_name', 'email']
    list_select_related = ('account',)


class ParentInline(admin.StackedInline):
    model = Parent
    extra = 0


class ScoutAdmin(admin.ModelAdmin):
    model = Scout
    list_display = ('short_name', 'last_name', 'age', 'status')
    list_display_links = ['short_name', 'last_name']
    list_filter = ('status', )


class ScoutInline(admin.StackedInline):
    model = Scout
    extra = 0


class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
    model = Account
    list_display = ('get_short_name', 'get_last_name', 'email', 'is_staff', 'is_active',)
    list_display_links = ['get_short_name', 'get_last_name', 'email']
    list_filter = ('email', 'is_staff', 'is_active',)
    list_select_related = ('profile',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
         ),
    )
    search_fields = ('email',)
    ordering = ('email',)
    inlines = (ParentInline,)

    def get_short_name(self, instance):
        return instance.profile.short_name()

    get_short_name.short_description = _('Name')

    def get_last_name(self, instance):
        return instance.profile.last_name

    get_last_name.short_description = _('Last Name')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(AccountAdmin, self).get_inline_instances(request, obj)


class FamilyAdmin(admin.ModelAdmin):
    inlines = (ParentInline, ScoutInline)


admin.site.unregister(Group)
admin.site.register(Parent, ParentAdmin)
admin.site.register(Scout, ScoutAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Family, FamilyAdmin)
