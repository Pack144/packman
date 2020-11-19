import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Case, Count, When, CharField
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _, ngettext

from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.widgets import ImageClearableFileInput

from address_book.forms import AddressForm, PhoneNumberForm
from address_book.models import Address, PhoneNumber
from committees.models import Membership as CommitteeMembership
from dens.models import Membership as DenMembership, Rank
from pack_calendar.models import PackYear
from . import forms, models

logger = logging.getLogger(__name__)


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar
    # just above the filter options.
    title = _("Ranks")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'rank'

    def lookups(self, request, model_admin):
        return Rank.RANK_CHOICES

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value() is None:
            return queryset
        else:
            return queryset.filter(
                den__den__rank__rank__exact=self.value()
            ).filter(
                den__year_assigned=PackYear.get_current_pack_year()
            ).distinct()


class FamilyListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar
    # just above the filter options.
    title = _("Family Members")

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
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value() == 'complete':
            return queryset.filter(
                adults__isnull=False, children__isnull=False
            ).distinct()
        if self.value() == 'empty':
            return queryset.filter(
                adults__isnull=True, children__isnull=True
            ).distinct()
        if self.value() == 'orphan':
            return queryset.filter(
                adults__isnull=True, children__isnull=False
            ).distinct()
        if self.value() == 'childless':
            return queryset.filter(
                adults__isnull=False, children__isnull=True
            ).distinct()


class AdultsBasedOnCubStatusFilter(admin.SimpleListFilter):
    title = _('Cub Status')
    parameter_name = 'cub_status'

    def lookups(self, request, model_admin):
        return models.Scout.STATUS_CHOICES

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value() is None:
            return queryset
        else:
            return queryset.filter(family__children__status=self.value()).distinct()


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
    actions = ['make_approved', 'make_active', 'make_inactive', 'make_graduated', 'continue_in_same_den_one_more_year']
    list_display = (
        'name',
        'last_name',
        'school',
        'get_grade',
        'age',
        'status',
        'current_den',
        'pack_comments',
        'date_added',
    )
    list_display_links = ('name', 'last_name')
    list_filter = ('status', AnimalRankListFilter, 'den__den')
    readonly_fields = (
        'date_added',
        'last_updated',
        'reference',
        'member_comments',
        'grade',
        'get_adults'
    )
    autocomplete_fields = ['family', 'school']
    inlines = [DenMembershipInline]
    search_fields = (
        'first_name',
        'middle_name',
        'nickname',
        'last_name',
        'family__adults__first_name',
        'family__adults__nickname',
        'family__adults__last_name',
    )
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }

    fieldsets = (
        (None, {'fields': (
            ('first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            'status',
            'slug'
        )}),
        (_("Family"), {
            'fields': ('family', 'get_adults')
        }),
        (_("School"), {
            'fields': ('school', ('started_school', 'grade'))
        }),
        (_("Important Dates"), {
            'classes': ('collapse',),
            'fields': ('date_of_birth', 'date_added', 'started_pack')
        }),
        (_("Comments"), {
            'classes': ('collapse',),
            'fields': ('member_comments', 'reference', 'pack_comments',),
        })
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            _name=Coalesce(
                Case(
                    When(nickname__exact="", then=None),
                    When(nickname__isnull=False, then="nickname"),
                    default=None,
                    output_field=CharField(),
                ),
                Case(
                    When(first_name__exact="", then=None),
                    When(first_name__isnull=False, then="first_name"),
                    default=None,
                    output_field=CharField(),
                ),
            )
        )
        return qs

    def name(self, obj):
        return obj._name

    name.admin_order_field = '_name'

    def get_adults(self, obj):
        display_text = ", ".join([
            "<a href={}>{}</a>".format(
                reverse('admin:{}_{}_change'.format(adult._meta.app_label, adult._meta.model_name),
                        args=(adult.pk,)),
                adult.get_full_name())
            for adult in obj.family.adults.all()
        ])
        if display_text:
            return mark_safe(display_text)
        else:
            return '-'
    get_adults.short_description = _('adults')

    def make_active(self, request, queryset):
        updated = queryset.update(status=models.Scout.ACTIVE)
        self.message_user(request, ngettext(
            '%d Cub was successfully marked as active.',
            '%d Cubs were successfully marked as active',
            updated
        ) % updated, messages.SUCCESS)

    def make_approved(self, request, queryset):
        updated = queryset.update(status=models.Scout.APPROVED)
        self.message_user(request, ngettext(
            '%d Cub was successfully marked as approved.',
            '%d Cubs were successfully marked as approved',
            updated
        ) % updated, messages.SUCCESS)

    def make_inactive(self, request, queryset):
        updated = queryset.update(status=models.Scout.INACTIVE)
        self.message_user(request, ngettext(
            '%d Cub was successfully marked as inactive.',
            '%d Cubs were successfully marked as inactive',
            updated
        ) % updated, messages.SUCCESS)

    def make_graduated(self, request, queryset):
        updated = queryset.update(status=models.Scout.GRADUATED)
        self.message_user(request, ngettext(
            '%d Cub was successfully marked as graduated.',
            '%d Cubs were successfully marked as graduated',
            updated
        ) % updated, messages.SUCCESS)

    def continue_in_same_den_one_more_year(self, request, queryset):
        next_year, created = PackYear.objects.get_or_create(year=PackYear.get_current_pack_year_year() + 1)
        n = queryset.count()
        if n:
            for obj in queryset:
                if obj.current_den:
                    m, c = DenMembership.objects.get_or_create(den=obj.current_den, scout=obj, year_assigned=next_year)
                    if not c:
                        self.message_user(request, _(
                            f'{obj} is already assigned to Den {obj.current_den} for the {next_year} Pack Year.'
                        ), messages.WARNING)
                        n -= 1
                else:
                    n -= 1
                    self.message_user(request, _(f'{obj} is not currently assigned to a den.'), messages.WARNING)
        self.message_user(request, ngettext(
            f'Successfully rolled {n} Cub into the {next_year} Pack Year.',
            f'Successfully rolled {n} Cubs into the {next_year} Pack Year.',
            n,
        ), messages.SUCCESS)

    make_active.short_description = _("Mark selected Cubs as active")
    make_approved.short_description = _("Approve selected Cubs for membership")
    make_inactive.short_description = _("Mark selected Cubs as inactive")
    make_graduated.short_description = _("Graduate selected Cubs")
    continue_in_same_den_one_more_year.short_description = _('Assign selected Cubs to the same den for the next Pack Year')


@admin.register(models.Adult)
class AdultAdmin(UserAdmin):
    add_form = forms.AdminAdultCreation
    form = forms.AdminAdultChange
    list_display = (
        'name',
        'last_name',
        'email',
        'active',
        'role',
        'is_staff',
        'is_superuser',
        'last_login'
    )
    list_display_links = ('name', 'last_name', 'email')
    list_filter = ('_is_staff', 'is_superuser', AdultsBasedOnCubStatusFilter)
    ordering = ('last_name', 'nickname', 'first_name')
    readonly_fields = ('date_added', 'last_updated', 'last_login', 'get_children')
    autocomplete_fields = ['family']
    search_fields = (
        'email',
        'first_name',
        'nickname',
        'last_name',
        'family__children__first_name',
        'family__children__nickname',
        'family__children__last_name',
    )
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }

    fieldsets = (
        (None, {'fields': (
            ('first_name', 'middle_name', 'last_name', 'suffix'),
            ('nickname', 'gender'),
            'photo',
            'role',
            'slug'
        )}),
        (_('Family'), {
            'fields': ('family', 'get_children')
        }),
        (_("Account Details"), {
            'fields': (('email', 'is_published'), 'password')
        }),
        (_("Permissions"), {
            'classes': ('collapse',),
            'fields': (
                'is_active', '_is_staff', 'is_superuser', 'groups',
                'user_permissions',
            ),
        }),
        (_("Important Dates"), {
            'classes': ('collapse',),
            'fields': ('date_of_birth', 'last_login', 'date_added')
        }),
        (_("Comments"), {
            'classes': ('collapse',),
            'fields': ('pack_comments',),
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            _name=Coalesce(
                Case(
                    When(nickname__exact="", then=None),
                    When(nickname__isnull=False, then="nickname"),
                    default=None,
                    output_field=CharField(),
                ),
                Case(
                    When(first_name__exact="", then=None),
                    When(first_name__isnull=False, then="first_name"),
                    default=None,
                    output_field=CharField(),
                ),
            )
        )
        return qs

    def name(self, obj):
        return obj._name

    name.admin_order_field = '_name'

    def get_children(self, obj):
        display_text = ", ".join([
            "<a href={}>{}</a>".format(
                reverse('admin:{}_{}_change'.format(child._meta.app_label, child._meta.model_name),
                        args=(child.pk,)),
                child.get_short_name())
            for child in obj.family.children.all()
        ])
        if display_text:
            return mark_safe(display_text)
        else:
            return '-'
    get_children.short_description = _('children')


@admin.register(models.Family)
class FamilyAdmin(admin.ModelAdmin):
    form = forms.FamilyForm
    list_display = ('name', 'adults_count', 'children_count',)
    list_filter = (FamilyListFilter,)
    search_fields = (
        'name',
        'adults__first_name',
        'adults__nickname',
        'adults__last_name',
        'children__first_name',
        'children__nickname',
        'children__last_name',
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _adults_count=Count('adults', distinct=True),
            _children_count=Count('children', distinct=True)
        )
        return queryset

    def adults_count(self, obj):
        return obj._adults_count

    adults_count.admin_order_field = '_adults_count'
    adults_count.short_description = _("Number of adults")

    def children_count(self, obj):
        return obj._children_count

    children_count.admin_order_field = '_children_count'
    children_count.short_description = _("Number of children")
