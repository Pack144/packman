from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from address_book.models import Address, PhoneNumber

from .forms import AccountCreationForm, AccountChangeForm
from .models import Account, Family, Parent, Scout


class AddressInline(admin.StackedInline):
    model = Address
    extra = 1


class PhoneNumberInline(admin.TabularInline):
    model = PhoneNumber
    extra = 1


class ParentInline(admin.StackedInline):
    model = Parent
    extra = 0
    can_delete = False


class ScoutInline(admin.StackedInline):
    model = Scout
    extra = 0
    can_delete = False


class ParentRelationshipInline(admin.TabularInline):
    model = Scout.parents.through
    extra = 0
    verbose_name = _('Parent')
    verbose_name_plural = _('Parents')


class ScoutAdmin(admin.ModelAdmin):
    model = Scout
    list_display = ('name', 'last_name', 'den', 'school', 'grade', 'age', 'status', )
    list_display_links = ['name', 'last_name']
    list_filter = ('status', 'den', )
    readonly_fields = ('date_added', 'last_updated', )
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name', 'email', )
    inlines = (ParentRelationshipInline, )


class ScoutParentInline(admin.TabularInline):
    model = Parent.children.through
    extra = 0
    verbose_name = _('Child')
    verbose_name_plural = _('Children')


class ParentAdmin(admin.ModelAdmin):
    model = Parent
    list_display = ('name', 'last_name', 'email', 'role')
    list_display_links = ['name', 'last_name', 'email']
    list_filter = ('role', )
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name', 'email', )
    list_select_related = ('account',)
    inlines = (ScoutParentInline, PhoneNumberInline, AddressInline,)
    exclude = ('children', )
    readonly_fields = ('date_added', 'last_updated', )


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
        return instance.profile.name

    get_short_name.short_description = _('Name')

    def get_last_name(self, instance):
        return instance.profile.last_name

    get_last_name.short_description = _('Last Name')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(AccountAdmin, self).get_inline_instances(request, obj)


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    fields = ('parents', 'children', )


admin.site.login = login_required(admin.site.login)
admin.site.unregister(Group)
admin.site.register(Scout, ScoutAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Parent, ParentAdmin)
