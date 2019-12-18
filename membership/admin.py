from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.widgets import ImageClearableFileInput

from address_book.models import Address, PhoneNumber

from .import forms, models


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar just above the filter options.
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


@admin.register(models.ChildMember)
class ScoutAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'nickname', 'last_name', 'den', 'school', 'grade', 'age', 'status', 'family')
    list_display_links = ['first_name', 'nickname', 'last_name']
    list_filter = ('status', AnimalRankListFilter, 'den')
    readonly_fields = ('date_added', 'last_updated', 'reference', 'member_comments')
    autocomplete_fields = ['family', 'school']
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name')
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }


@admin.register(models.AdultMember)
class AdultAdmin(UserAdmin):
    add_form = forms.AdultMemberCreation
    form = forms.AdultMemberChange
    list_display = ('first_name', 'middle_name', 'last_name', 'email', 'role', 'family', 'is_staff', 'is_superuser')
    list_display_links = ('first_name', 'middle_name', 'last_name', 'email')
    list_filter = ('is_staff', 'is_superuser')
    ordering = ('last_name', 'nickname', 'first_name')
    readonly_fields = ('date_added', 'last_updated', 'last_login')
    autocomplete_fields = ['family']
    search_fields = ('email', 'first_name', 'nickname', 'last_name')
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }

    fieldsets = (
        (None, {'fields': (
            ('first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            ('role', 'family'),
            'slug'
        )}),
        (_('Account Details'), {'fields': ('email', 'is_subscribed', 'is_published', 'password')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important Dates'), ({'fields': ('last_login', 'date_added')})),
    )
    add_fieldsets = (
        (None, {'fields': (
            ('first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            'slug',
        )}),
        (_('Account Details'), {'fields': (
            ('email', 'password1', 'password2'))}),
    )
    inlines = [PhoneNumberInline, AddressInline]


class AdultInline(admin.TabularInline):
    model = models.AdultMember
    autocomplete_fields = ['adults']


@admin.register(models.Family)
class FamilyAdmin(admin.ModelAdmin):
    # form = forms.Family
    list_display = ('name', 'get_adults_count', 'get_children_count',)
    search_fields = ('name', )

    def get_adults_count(self, instance):
        return instance.adults.count()

    get_adults_count.short_description = _('Number of adults')

    def get_children_count(self, instance):
        return instance.children.count()

    get_children_count.short_description = _('Number of children')


admin.site.login = login_required(admin.site.login)
admin.site.unregister(Group)
