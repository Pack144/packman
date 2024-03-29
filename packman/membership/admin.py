import csv
import logging
from io import StringIO
from zipfile import ZipFile

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Case, CharField, Count, When
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.widgets import ImageClearableFileInput

from packman.address_book.forms import AddressForm, PhoneNumberForm
from packman.address_book.models import Address, PhoneNumber
from packman.calendars.models import PackYear
from packman.committees.models import CommitteeMember
from packman.dens.models import Membership as DenMembership
from packman.dens.models import Rank

from . import forms, models

logger = logging.getLogger(__name__)


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar
    # just above the filter options.
    title = _("Ranks")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "rank"

    def lookups(self, request, model_admin):
        return Rank.RankChoices.choices

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value() is None:
            return queryset
        else:
            return (
                queryset.filter(den_memberships__den__rank__rank__exact=self.value())
                .filter(den_memberships__year_assigned=PackYear.objects.current())
                .distinct()
            )


class FamilyListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the right admin sidebar
    # just above the filter options.
    title = _("Family Members")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "members"

    def lookups(self, request, model_admin):
        return (
            ("complete", _("Parents and Cubs")),
            ("childless", _("No children")),
            ("orphan", _("No parents")),
            ("empty", _("No family members")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value() == "complete":
            return queryset.filter(adults__isnull=False, children__isnull=False).distinct()
        if self.value() == "empty":
            return queryset.filter(adults__isnull=True, children__isnull=True).distinct()
        if self.value() == "orphan":
            return queryset.filter(adults__isnull=True, children__isnull=False).distinct()
        if self.value() == "childless":
            return queryset.filter(adults__isnull=False, children__isnull=True).distinct()


class AdultsBasedOnCubStatusFilter(admin.SimpleListFilter):
    title = _("Cub Status")
    parameter_name = "cub_status"

    def lookups(self, request, model_admin):
        return models.Scout.STATUS_CHOICES + ((7, _("Eligible for Next Year")),)

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value() is None:
            return queryset
        elif self.value() == "7":
            return queryset.filter(
                family__children__den_memberships__year_assigned=PackYear.objects.current(),
                family__children__den_memberships__den__rank__rank__lte=Rank.RankChoices.JR_WEBE,
                family__children__status=models.Scout.ACTIVE,
            ).distinct()

        else:
            return queryset.filter(family__children__status=self.value()).distinct()


class AddressInline(admin.StackedInline):
    extra = 0
    form = AddressForm
    model = Address


class CommitteeMemberInline(admin.TabularInline):
    extra = 0
    model = CommitteeMember
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
    actions = [
        "make_approved",
        "make_active",
        "make_inactive",
        "make_graduated",
        "continue_in_same_den_one_more_year",
        "export_as_csv",
    ]
    list_display = (
        "name",
        "last_name",
        "school",
        "get_grade",
        "age",
        "status",
        "current_den",
        "pack_comments",
        "date_added",
    )
    list_display_links = ("name", "last_name")
    list_filter = ("status", AnimalRankListFilter, "den_memberships__den", "date_added")
    readonly_fields = (
        "date_added",
        "last_updated",
        "reference",
        "member_comments",
        "grade",
        "get_adults",
    )
    autocomplete_fields = ["family", "school"]
    inlines = [DenMembershipInline]
    search_fields = (
        "first_name",
        "middle_name",
        "nickname",
        "last_name",
        "family__adults__first_name",
        "family__adults__nickname",
        "family__adults__last_name",
    )
    formfield_overrides = {
        ThumbnailerImageField: {"widget": ImageClearableFileInput},
    }

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("first_name", "middle_name", "last_name", "suffix"),
                    ("nickname", "gender"),
                    "photo",
                    "status",
                    "slug",
                )
            },
        ),
        (_("Family"), {"fields": ("family", "get_adults")}),
        (_("School"), {"fields": ("school", ("started_school", "grade"))}),
        (
            _("Important Dates"),
            {
                "classes": ("collapse",),
                "fields": ("date_of_birth", "date_added", "started_pack"),
            },
        ),
        (
            _("Comments"),
            {
                "classes": ("collapse",),
                "fields": (
                    "member_comments",
                    "reference",
                    "pack_comments",
                ),
            },
        ),
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

    @admin.display(ordering="_name")
    def name(self, obj):
        return obj._name

    @admin.display(description=_("adults"))
    def get_adults(self, obj):
        adult_links = format_html_join(
            "",
            "<li><a href={}>{}</a></li>",
            (
                (
                    reverse(
                        f"admin:{adult._meta.app_label}_{adult._meta.model_name}_change",
                        args=(adult.pk,),
                    ),
                    adult.get_short_name(),
                )
                for adult in obj.family.adults.all()
            ),
        )
        return format_html("<ul>{}</ul>", adult_links) if adult_links else "-"

    @admin.action(description=_("Mark selected Cubs as active"))
    def make_active(self, request, queryset):
        updated = queryset.order_by().update(status=models.Scout.ACTIVE)
        self.message_user(
            request,
            ngettext(
                "%d Cub was successfully marked as active.",
                "%d Cubs were successfully marked as active",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Approve selected Cubs for membership"))
    def make_approved(self, request, queryset):
        updated = queryset.order_by().update(status=models.Scout.APPROVED)
        self.message_user(
            request,
            ngettext(
                "%d Cub was successfully marked as approved.",
                "%d Cubs were successfully marked as approved",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Mark selected Cubs as inactive"))
    def make_inactive(self, request, queryset):
        updated = queryset.order_by().update(status=models.Scout.INACTIVE)
        self.message_user(
            request,
            ngettext(
                "%d Cub was successfully marked as inactive.",
                "%d Cubs were successfully marked as inactive",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Graduate selected Cubs"))
    def make_graduated(self, request, queryset):
        updated = queryset.order_by().update(status=models.Scout.GRADUATED)
        self.message_user(
            request,
            ngettext(
                "%d Cub was successfully marked as graduated.",
                "%d Cubs were successfully marked as graduated",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description=_("Assign selected Cubs to the same den for the next Pack Year"))
    def continue_in_same_den_one_more_year(self, request, queryset):
        next_year, created = PackYear.objects.get_or_create(year=PackYear.get_current().pk + 1)
        n = queryset.count()
        if n:
            for obj in queryset:
                if obj.current_den:
                    m, c = DenMembership.objects.get_or_create(den=obj.current_den, scout=obj, year_assigned=next_year)
                    if not c:
                        self.message_user(
                            request,
                            _(f"{obj} is already assigned to Den {obj.current_den} for the {next_year} Pack Year."),
                            messages.WARNING,
                        )
                        n -= 1
                else:
                    n -= 1
                    self.message_user(
                        request,
                        _(f"{obj} is not currently assigned to a den."),
                        messages.WARNING,
                    )
        self.message_user(
            request,
            ngettext(
                f"Successfully rolled {n} Cub into the {next_year} Pack Year.",
                f"Successfully rolled {n} Cubs into the {next_year} Pack Year.",
                n,
            ),
            messages.SUCCESS,
        )

    @admin.action(description=_("Export selected Cubs to CSV file"))
    def export_as_csv(self, request, queryset):
        # Export the selected Cubs for use in GrandPrix Race Manager
        meta = self.model._meta
        field_names = [
            "LastName",
            "FirstName",
            "Group",
            "Subgroup",
            "VehicleNumber",
            "VehicleName",
            "Passed",
            "Image",
            "Exclude",
            "Printed",
        ]

        response = HttpResponse(content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={meta}.zip"

        csv_file = StringIO()
        writer = csv.writer(csv_file)

        writer.writerow(field_names)
        with ZipFile(response, "w") as zip_obj:
            for obj in queryset:
                fields = {
                    "LastName": obj.last_name,
                    "FirstName": obj.get_short_name(),
                    "Group": obj.rank,
                    "Subgroup": obj.current_den,
                    "VehicleNumber": "",
                    "VehicleName": "",
                    "Passed": "No",
                    "Image": "",
                    "Exclude": "No",
                    "Printed": "No",
                }
                if obj.photo:
                    fields["Image"] = f"{fields['FirstName']}{fields['LastName']}.jpg"
                    zip_obj.write(obj.photo["320x320"].path, fields["Image"])
                writer.writerow([fields[field] for field in fields])

            zip_obj.writestr("roster.csv", csv_file.getvalue())

        return response


@admin.register(models.Adult)
class AdultAdmin(UserAdmin):
    actions = ["export_as_csv"]
    add_form = forms.AdminAdultCreation
    form = forms.AdminAdultChange
    list_display = (
        "name",
        "last_name",
        "email",
        "active",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_added",
    )
    list_display_links = ("name", "last_name", "email")
    list_filter = (
        "_is_staff",
        "is_superuser",
        AdultsBasedOnCubStatusFilter,
        "role",
        "date_added",
    )
    list_select_related = ("family",)
    ordering = ("last_name", "nickname", "first_name")
    readonly_fields = ("date_added", "last_updated", "last_login", "get_children")
    autocomplete_fields = ["family"]
    search_fields = (
        "email",
        "first_name",
        "nickname",
        "last_name",
        "family__children__first_name",
        "family__children__nickname",
        "family__children__last_name",
    )
    formfield_overrides = {
        ThumbnailerImageField: {"widget": ImageClearableFileInput},
    }

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("first_name", "middle_name", "last_name", "suffix"),
                    ("nickname", "gender"),
                    "photo",
                    "role",
                    "slug",
                )
            },
        ),
        (_("Family"), {"fields": ("family", "get_children")}),
        (_("Account Details"), {"fields": (("email", "is_published"), "password")}),
        (
            _("Permissions"),
            {
                "classes": ("collapse",),
                "fields": (
                    "is_active",
                    "_is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important Dates"),
            {
                "classes": ("collapse",),
                "fields": ("date_of_birth", "last_login", "date_added"),
            },
        ),
        (
            _("Comments"),
            {
                "classes": ("collapse",),
                "fields": ("pack_comments",),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    ("first_name", "middle_name", "last_name", "suffix"),
                    ("nickname", "gender"),
                    "photo",
                    "slug",
                )
            },
        ),
        (_("Account Details"), {"fields": (("email", "password1", "password2"),)}),
    )
    inlines = [PhoneNumberInline, AddressInline, CommitteeMemberInline]

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

    @admin.display(ordering="_name")
    def name(self, obj):
        return obj._name

    @admin.display(description=_("children"))
    def get_children(self, obj):
        children_links = format_html_join(
            "",
            "<li><a href={}>{}</a></li>",
            (
                (
                    reverse(
                        f"admin:{child._meta.app_label}_{child._meta.model_name}_change",
                        args=(child.pk,),
                    ),
                    child.get_short_name(),
                )
                for child in obj.family.children.all()
            ),
        )
        return format_html("<ul>{}</ul>", children_links) if children_links else "-"

    @admin.action(description=_("Export selected Adults"))
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={meta}.csv"
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response


@admin.register(models.Family)
class FamilyAdmin(admin.ModelAdmin):
    form = forms.FamilyForm
    list_display = (
        "name",
        "adults_count",
        "children_count",
    )
    list_filter = (FamilyListFilter,)
    search_fields = (
        "name",
        "adults__first_name",
        "adults__nickname",
        "adults__last_name",
        "children__first_name",
        "children__nickname",
        "children__last_name",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _adults_count=Count("adults", distinct=True),
            _children_count=Count("children", distinct=True),
        )
        return queryset

    @admin.display(
        description=_("Number of adults"),
        ordering="_adults_count",
    )
    def adults_count(self, obj):
        return obj._adults_count

    @admin.display(
        description=_("Number of children"),
        ordering="_children_count",
    )
    def children_count(self, obj):
        return obj._children_count
