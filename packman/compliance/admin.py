from django.contrib import admin, messages
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from packman.calendars.models import PackYear

from .models import Requirement, RequirementRecord


class PackYearFilter(admin.SimpleListFilter):
    """
    A "pack year" filter that defaults to the current year when the changelist
    is first opened, rather than showing every year's records at once.

    Modelled on campaigns.admin.CampaignFilter, including the "all" sentinel
    that makes "no query param" and "explicitly chose All" distinguishable.
    """

    title = _("pack year")
    parameter_name = "year__year__exact"

    def lookups(self, request, model_admin):
        return [(year.pk, str(year)) for year in PackYear.objects.all()]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "all":
            return queryset
        if value in (None, ""):
            current = PackYear.get_current()
            return queryset.filter(year=current) if current else queryset
        return queryset.filter(year__pk=value)

    def choices(self, changelist):
        current = PackYear.get_current()
        yield {
            "selected": self.value() == "all",
            "query_string": changelist.get_query_string({self.parameter_name: "all"}),
            "display": _("All"),
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": (self.value() is None and current is not None and str(lookup) == str(current.pk))
                or self.value() == str(lookup),
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }


class MemberRequirementRecordInline(admin.TabularInline):
    """
    Serves both ScoutAdmin and AdultAdmin. The foreign key points at Member,
    which both inherit from, so one inline covers both change pages.
    """

    model = RequirementRecord
    fk_name = "member"
    extra = 0
    autocomplete_fields = ("requirement",)
    fields = ("requirement", "year", "status", "completed_on", "notes")
    verbose_name = _("Membership Requirement")
    verbose_name_plural = _("Membership Requirements")


class FamilyRequirementRecordInline(admin.TabularInline):
    model = RequirementRecord
    fk_name = "family"
    extra = 0
    autocomplete_fields = ("requirement",)
    fields = ("requirement", "year", "status", "completed_on", "notes")
    verbose_name = _("Family Requirement")
    verbose_name_plural = _("Family Requirements")

    def get_queryset(self, request):
        # Family-scoped records only; the members' own records belong on their
        # pages, not repeated on the family's.
        return super().get_queryset(request).filter(member__isnull=True)


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "applies_to",
        "include_contributors",
        "is_active",
        "sort_order",
        "record_count",
    )
    list_display_links = ("name",)
    list_editable = ("sort_order", "is_active")
    list_filter = ("applies_to", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug", "description")
    actions = ["sync_records_current_year", "sync_records_next_year"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "is_active", "sort_order")}),
        (_("Who it applies to"), {"fields": ("applies_to", "include_contributors")}),
    )

    def get_queryset(self, request):
        current = PackYear.get_current()
        return (
            super()
            .get_queryset(request)
            .annotate(record_count=Count("record", filter=Q(record__year=current) if current else Q()))
        )

    @admin.display(description=_("records this year"), ordering="record_count")
    def record_count(self, obj):
        return obj.record_count

    def _sync(self, request, queryset, year, label):
        if year is None:
            self.message_user(
                request, _("There is no %(label)s pack year to sync.") % {"label": label}, messages.ERROR
            )
            return

        opened = sum(len(requirement.sync_records(year=year)) for requirement in queryset)
        self.message_user(
            request,
            ngettext(
                "%(count)d record opened for %(year)s.",
                "%(count)d records opened for %(year)s.",
                opened,
            )
            % {"count": opened, "year": year},
            messages.SUCCESS,
        )

    @admin.action(description=_("Open records for the current Pack Year"))
    def sync_records_current_year(self, request, queryset):
        self._sync(request, queryset, PackYear.get_current(), _("current"))

    @admin.action(description=_("Open records for the next Pack Year"))
    def sync_records_next_year(self, request, queryset):
        self._sync(request, queryset, PackYear.objects.next(), _("next"))


@admin.register(RequirementRecord)
class RequirementRecordAdmin(admin.ModelAdmin):
    list_display = (
        "requirement",
        "subject",
        "year",
        "status",
        "completed_on",
        "recorded_by",
    )
    list_display_links = ("requirement", "subject")
    list_filter = ("requirement", PackYearFilter, "status")
    list_select_related = ("requirement", "year", "member", "family", "recorded_by")
    autocomplete_fields = ("member", "family", "recorded_by")
    date_hierarchy = "completed_on"
    actions = ["mark_complete", "mark_waived"]
    search_fields = (
        "member__first_name",
        "member__nickname",
        "member__last_name",
        "family__name",
        "requirement__name",
    )
    fieldsets = (
        (None, {"fields": ("requirement", "year")}),
        (_("Who"), {"fields": ("member", "family")}),
        (_("Standing"), {"fields": ("status", "completed_on", "notes", "recorded_by")}),
    )

    @admin.display(description=_("who"), ordering="member__last_name")
    def subject(self, obj):
        return obj.subject

    def save_model(self, request, obj, form, change):
        # Record who entered it, unless someone set that deliberately.
        if not obj.recorded_by_id:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_("Mark selected records complete as of today"))
    def mark_complete(self, request, queryset):
        today = timezone.localdate()
        updated = 0
        for record in queryset:
            record.status = RequirementRecord.Status.COMPLETE
            record.completed_on = today
            record.recorded_by = request.user
            record.save()
            updated += 1

        self.message_user(
            request,
            ngettext("%(count)d record marked complete.", "%(count)d records marked complete.", updated)
            % {"count": updated},
            messages.SUCCESS,
        )

    @admin.action(description=_("Waive selected records"))
    def mark_waived(self, request, queryset):
        updated = queryset.update(status=RequirementRecord.Status.WAIVED, recorded_by=request.user)
        self.message_user(
            request,
            ngettext("%(count)d record waived.", "%(count)d records waived.", updated) % {"count": updated},
            messages.SUCCESS,
        )
