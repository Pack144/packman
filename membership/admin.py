from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from address_book.models import Address, PhoneNumber

from .forms import AccountCreationForm, AccountChangeForm, FamilyForm
from .models import Account, Family, Parent, Scout


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('ranks')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'ranks'

    def lookups(self, request, model_admin):
        return (
            ('tigers', _('Tigers')),
            ('wolves', _('Wolves')),
            ('bears', _('Bears')),
            ('jr_weebs', _('Jr. Webelos')),
            ('sr_weebs', _('Sr. Webelos')),
            ('animals', _('Animal Ranks')),
            ('webelos', _('Webelos')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'tigers':
            return queryset.filter(den__rank__exact=2)
        if self.value() == 'wolves':
            return queryset.filter(den__rank__exact=3)
        if self.value() == 'bears':
            return queryset.filter(den__rank__exact=4)
        if self.value() == 'jr_weebs':
            return queryset.filter(den__rank__exact=5)
        if self.value() == 'sr_weebs':
            return queryset.filter(den__rank__exact=6)
        if self.value() == 'animals':
            return queryset.filter(den__rank__lte=4)
        if self.value() == 'webelos':
            return queryset.filter(den__rank__gte=5)


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
    list_display = ('first_name', 'nickname', 'last_name', 'den', 'school', 'grade', 'age', 'status', 'family')
    list_display_links = ['first_name', 'nickname', 'last_name']
    list_filter = ('status', AnimalRankListFilter, 'den')
    readonly_fields = ('date_added', 'last_updated')
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name', 'email')


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'nickname', 'last_name', 'role', 'family')
    list_display_links = ['first_name', 'nickname', 'last_name']
    list_filter = ('role', )
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name', 'email')
    list_select_related = ('account',)
    inlines = (PhoneNumberInline, AddressInline, )
    exclude = ('children', )
    readonly_fields = ('date_added', 'last_updated', )


@admin.register(Account)
class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
    list_display = ('get_short_name', 'get_last_name', 'email', 'is_active', 'is_staff', 'is_superuser')
    list_display_links = ['get_short_name', 'get_last_name', 'email']
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    list_select_related = ('profile',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active', 'is_superuser')}
         ),
    )
    search_fields = ('email',)
    ordering = ('email',)
    inlines = (ParentInline, )

    def get_short_name(self, instance):
        return instance.profile.name

    get_short_name.short_description = _('Name')
    get_short_name.admin_order_field = 'profile'

    def get_last_name(self, instance):
        return instance.profile.last_name

    get_last_name.short_description = _('Last Name')
    get_last_name.admin_order_field = 'profile__last_name'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(AccountAdmin, self).get_inline_instances(request, obj)


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    form = FamilyForm
    list_display = ('__str__', 'get_parents_count', 'get_children_count', )

    def get_parents_count(self, instance):
        return instance.parents.count()

    get_parents_count.short_description = _('Number of parents')

    def get_children_count(self, instance):
        return instance.children.count()

    get_children_count.short_description = _('Number of children')


admin.site.login = login_required(admin.site.login)
admin.site.unregister(Group)
