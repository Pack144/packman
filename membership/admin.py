from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from guardian.admin import GuardedModelAdmin

from .forms import AccountCreationForm, AccountChangeForm
from .models import Account, Parent, Scout


class ParentInline(admin.StackedInline):
    model = Parent
    extra = 0
    can_delete = False


class ScoutAdmin(GuardedModelAdmin):
    model = Scout
    list_display = ('short_name', 'last_name', 'age', 'status')
    list_display_links = ['short_name', 'last_name']
    list_filter = ('status', )
    readonly_fields = ('get_parents',)

    def get_parents(self, instance):
        return instance.parents.all()


class ScoutInline(admin.StackedInline):
    model = Scout
    extra = 0


class ParentAdmin(GuardedModelAdmin):
    model = Parent
    list_display = ('short_name', 'last_name', 'email', 'status', 'role')
    list_display_links = ['short_name', 'last_name', 'email']
    list_filter = ('status', 'role')
    list_select_related = ('account',)


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
    inlines = (ParentInline, )

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


admin.site.unregister(Group)
# admin.site.register(Parent, ParentAdmin)
admin.site.register(Scout, ScoutAdmin)
admin.site.register(Account, AccountAdmin)