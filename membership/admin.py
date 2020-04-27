from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.widgets import ImageClearableFileInput

from address_book.models import Address, PhoneNumber
from address_book.forms import AddressForm, PhoneNumberForm
from dens.models import Rank
from pack_calendar.models import PackYear

from committees.models import Membership as CommitteeMembership
from dens.models import Membership as DenMembership

from . import forms, models


def make_active(modeladmin, request, queryset):
    queryset.update(status=models.Scout.ACTIVE)


def make_approved(modeladmin, request, queryset):
    queryset.update(status=models.Scout.APPROVED)


def make_inactive(modeladmin, request, queryset):
    queryset.update(status=models.Scout.INACTIVE)


make_active.short_description = _("Mark selected Cubs active")
make_approved.short_description = _("Approve selected Cubs for membership")
make_inactive.short_description = _("Mark selected Cubs inactive")


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar just above the filter options.
    title = _("Ranks")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'rank'

    def lookups(self, request, model_admin):
        return (
            ('tigers', _("Tigers")),
            ('wolves', _("Wolves")),
            ('bears', _("Bears")),
            ('jr_weebs', _("Jr. Webelos")),
            ('sr_weebs', _("Sr. Webelos")),
            ('animals', _("Animal Ranks")),
            ('webelos', _("Webelos")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'tigers':
            return queryset.filter(den__den__rank__rank__exact=Rank.TIGER).filter(den__year_assigned=PackYear.get_current_pack_year())
        if self.value() == 'wolves':
            return queryset.filter(den__den__rank__rank__exact=Rank.WOLF).filter(den__year_assigned=PackYear.get_current_pack_year())
        if self.value() == 'bears':
            return queryset.filter(den__den__rank__rank__exact=Rank.BEAR).filter(den__year_assigned=PackYear.get_current_pack_year())
        if self.value() == 'jr_weebs':
            return queryset.filter(den__den__rank__rank__exact=Rank.JR_WEBE).filter(den__year_assigned=PackYear.get_current_pack_year())
        if self.value() == 'sr_weebs':
            return queryset.filter(den__den__rank__rank__exact=Rank.SR_WEBE).filter(den__year_assigned=PackYear.get_current_pack_year())
        if self.value() == 'animals':
            return queryset.filter(den__den__rank__rank__lte=Rank.BEAR).filter(den__year_assigned=PackYear.get_current_pack_year())
        if self.value() == 'webelos':
            return queryset.filter(den__den__rank__rank__gte=Rank.JR_WEBE).filter(den__year_assigned=PackYear.get_current_pack_year())


class FamilyListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar just above the filter options.
    title = _('Family Members')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'members'

    def lookups(self, request, model_admin):
        return (
            ('complete', _("Parents and Cubs")),
            ('childless', _("No children")),
            ('orphan', _("No parents")),
            ('empty', _("No family members")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'complete':
            return queryset.filter(adults__isnull=False, children__isnull=False).distinct()
        if self.value() == 'empty':
            return queryset.filter(adults__isnull=True, children__isnull=True).distinct()
        if self.value() == 'orphan':
            return queryset.filter(adults__isnull=True, children__isnull=False).distinct()
        if self.value() == 'childless':
            return queryset.filter(adults__isnull=False, children__isnull=True).distinct()


class AddressInline(admin.StackedInline):
    extra = 0
    form = AddressForm
    model = Address


class CommitteeMembershipInline(admin.TabularInline):
    extra = 0
    model = CommitteeMembership
    verbose_name_plural = _("Committee Assignments")


class DenMembershipInline(admin.TabularInline):
    extra = 0
    model = DenMembership
    verbose_name_plural = _("Den Assignments")


class PhoneNumberInline(admin.TabularInline):
    extra = 0
    form = PhoneNumberForm
    model = PhoneNumber


@admin.register(models.Scout)
class ScoutAdmin(admin.ModelAdmin):
    actions = [make_approved, make_active, make_inactive]
    list_display = ('first_name', 'nickname', 'last_name', 'school', 'get_grade', 'age', 'status')
    list_display_links = ['first_name', 'nickname', 'last_name']
    list_filter = ('status', AnimalRankListFilter, 'den__den')
    readonly_fields = ('date_added', 'last_updated', 'reference', 'member_comments', 'grade')
    autocomplete_fields = ['family', 'school']
    inlines = [DenMembershipInline]
    search_fields = ('first_name', 'middle_name', 'nickname', 'last_name')
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }

    fieldsets = (
        (None, {'fields': (
            ('prefix', 'first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            ('status', 'family'),
            'slug'
        )}),
        (_("School"), {
            'fields': ('school', ('started_school', 'grade'))
        }),
        (_("Important Dates"), {
            'classes': ('collapse',),
            'fields': ('date_of_birth', 'date_added', 'started_pack')
        }),
        (_("Comments"), {
            'classes': ('collapse', ),
            'fields': ('member_comments', 'reference', 'pack_comments',),
        })
    )


@admin.register(models.Adult)
class AdultAdmin(UserAdmin):
    add_form = forms.AdminAdultCreation
    form = forms.AdminAdultChange
    list_display = ('first_name', 'middle_name', 'last_name', 'email', 'role', '_is_staff', 'is_superuser', 'last_login')
    list_display_links = ('first_name', 'middle_name', 'last_name', 'email')
    list_filter = ('_is_staff', 'is_superuser')
    ordering = ('last_name', 'nickname', 'first_name')
    readonly_fields = ('date_added', 'last_updated', 'last_login')
    autocomplete_fields = ['family']
    search_fields = ('email', 'first_name', 'nickname', 'last_name')
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }

    fieldsets = (
        (None, {'fields': (
            ('prefix', 'first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            ('role', 'family'),
            'slug'
        )}),
        (_("Account Details"), {
            'fields': (('email', 'is_published'), 'password')
        }),
        (_("Permissions"), {
            'classes': ('collapse',),
            'fields': ('is_active', '_is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_("Important Dates"), {
            'classes': ('collapse',),
            'fields': ('date_of_birth', 'last_login', 'date_added')
        }),
        (_("Comments"), {
            'classes': ('collapse', ),
            'fields': ('pack_comments', ),
        })
    )
    add_fieldsets = (
        (None, {'fields': (
            ('first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            'slug',
        )}),
        (_("Account Details"), {'fields': (
            ('email', 'password1', 'password2'))}),
    )
    inlines = [PhoneNumberInline, AddressInline, CommitteeMembershipInline]


@admin.register(models.Family)
class FamilyAdmin(admin.ModelAdmin):
    form = forms.Family
    list_display = ('name', 'get_adults_count', 'get_children_count',)
    list_filter = (FamilyListFilter,)
    search_fields = ('name',
                     'adults__first_name',
                     'adults__nickname',
                     'adults__last_name',
                     'children__first_name',
                     'children__nickname',
                     'children__last_name')

    def get_adults_count(self, instance):
        return instance.adults.count()

    get_adults_count.short_description = _("Number of adults")

    def get_children_count(self, instance):
        return instance.children.count()

    get_children_count.short_description = _("Number of children")


admin.site.login = login_required(admin.site.login)
