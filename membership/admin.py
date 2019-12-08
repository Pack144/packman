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
    extra = 0


class PhoneNumberInline(admin.TabularInline):
    model = PhoneNumber
    extra = 0


class ParentInline(admin.StackedInline):
    model = Parent
    extra = 0
    can_delete = False


@admin.register(Scout)
class ScoutAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_name', 'den', 'school', 'grade', 'age', 'status', )
    list_display_links = ['name', 'last_name']
    list_filter = ('status', 'den', )
    readonly_fields = ('date_added', 'last_updated', )
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name', 'email', )


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_name', 'email', 'role', 'family', )
    list_display_links = ['name', 'last_name', 'email']
    list_filter = ('role', )
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name', 'email', )
    list_select_related = ('account',)
    inlines = (PhoneNumberInline, AddressInline, )
    exclude = ('children', )
    readonly_fields = ('date_added', 'last_updated', )


@admin.register(Account)
class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
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
    pass


admin.site.login = login_required(admin.site.login)
admin.site.unregister(Group)
