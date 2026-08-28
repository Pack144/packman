from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Min, Prefetch, Q
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from packman.membership.mixins import ActiveMemberOrContributorTest
from packman.membership.models import Family

from .managers import EXPIRING_WINDOW
from .mixins import PackYearContextMixin, UserIsOwnFamilyOrLeadershipTest
from .models import Requirement, RequirementRecord


class RequirementRollupMixin:
    """
    Counts each requirement's standing for a pack year in a single query.

    Follows the DenQuerySet.counting_members() idiom -- one annotate with
    filtered Counts -- rather than looping and querying per requirement.
    """

    def get_requirement_rollup(self, year):
        today = timezone.localdate()
        soon = today + timezone.timedelta(days=EXPIRING_WINDOW)
        complete = Q(record__status=RequirementRecord.Status.COMPLETE)
        in_year = Q(record__year=year)
        unexpired = Q(record__expires_on__isnull=True) | Q(record__expires_on__gt=soon)

        return (
            Requirement.objects.active()
            .annotate(
                total=Count("record", filter=in_year, distinct=True),
                complete=Count("record", filter=in_year & complete & unexpired, distinct=True),
                expiring=Count(
                    "record",
                    filter=in_year & complete & Q(record__expires_on__gte=today, record__expires_on__lte=soon),
                    distinct=True,
                ),
                expired=Count("record", filter=in_year & complete & Q(record__expires_on__lt=today), distinct=True),
                waived=Count(
                    "record", filter=in_year & Q(record__status=RequirementRecord.Status.WAIVED), distinct=True
                ),
                outstanding=Count(
                    "record", filter=in_year & Q(record__status=RequirementRecord.Status.NOT_STARTED), distinct=True
                ),
            )
            .order_by("sort_order", "name")
        )


class ComplianceDashboardView(PermissionRequiredMixin, PackYearContextMixin, RequirementRollupMixin, TemplateView):
    """Where leadership sees who still owes what."""

    permission_required = "compliance.view_all_records"
    template_name = "compliance/dashboard.html"
    year_url_name = "compliance:dashboard_by_year"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = context["years"]["viewing"]
        requirements = list(self.get_requirement_rollup(year))

        context["requirements"] = requirements
        context["matrix"] = self.get_matrix(year, requirements)
        context["filter"] = self.request.GET.get("filter", "")
        context["den"] = self.request.GET.get("den", "")
        return context

    def get_matrix(self, year, requirements):
        """
        A family-by-requirement grid.

        Three queries: the rollup above, one aggregate over every record in the
        year, and one for the families. Deliberately not the per-row query loop
        that campaigns' OrderLeaderboardView uses.
        """
        today = timezone.localdate()
        soon = today + timezone.timedelta(days=EXPIRING_WINDOW)
        complete = Q(status=RequirementRecord.Status.COMPLETE)

        cells = {
            (row["family_id"], row["requirement_id"]): row
            for row in RequirementRecord.objects.filter(year=year, family__isnull=False)
            .values("family_id", "requirement_id")
            .annotate(
                total=Count("pk"),
                outstanding=Count("pk", filter=Q(status=RequirementRecord.Status.NOT_STARTED)),
                expired=Count("pk", filter=complete & Q(expires_on__lt=today)),
                expiring=Count("pk", filter=complete & Q(expires_on__gte=today, expires_on__lte=soon)),
                soonest_expiry=Min("expires_on", filter=complete),
            )
        }

        families = Family.objects.filter(pk__in=Family.objects.active_in(year).values("pk")).order_by("name")
        if den := self.request.GET.get("den"):
            families = families.filter(children__den_memberships__den__number=den).distinct()

        wanted = self.request.GET.get("filter")
        rows = []
        for family in families:
            cell_row = [cells.get((family.pk, requirement.pk)) for requirement in requirements]
            if wanted and not self.row_matches(cell_row, wanted):
                continue
            rows.append({"family": family, "cells": cell_row})
        return rows

    @staticmethod
    def row_matches(cells, wanted):
        if wanted not in ("outstanding", "expiring", "expired"):
            return True
        return any(cell and cell[wanted] for cell in cells)


class RequirementRosterView(PermissionRequiredMixin, PackYearContextMixin, RequirementRollupMixin, DetailView):
    """
    One requirement, everyone it applies to.

    Built from the subject side rather than from the records, so a Cub who
    joined after the year was synced still appears with nothing recorded.
    """

    permission_required = "compliance.view_all_records"
    template_name = "compliance/requirement_roster.html"
    context_object_name = "requirement"
    model = Requirement
    year_url_name = "compliance:roster_by_year"

    def get_year_url_kwargs(self):
        return {"slug": self.kwargs["slug"]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = context["years"]["viewing"]
        requirement = self.object

        records = RequirementRecord.objects.filter(requirement=requirement, year=year).select_related(
            "recorded_by", "requirement"
        )
        subjects = requirement.subjects_for(year).prefetch_related(
            Prefetch("requirement_records", queryset=records, to_attr="_records")
        )
        subjects = (
            subjects.select_related("family").order_by("last_name", "first_name")
            if requirement.tracks_member
            else subjects.order_by("name")
        )

        context["rows"] = [{"subject": subject, "record": self.record_for(subject)} for subject in subjects]
        context["counts"] = self.get_requirement_rollup(year).filter(pk=requirement.pk).first()
        return context

    @staticmethod
    def record_for(subject):
        records = getattr(subject, "_records", [])
        return records[0] if records else None


class FamilyComplianceView(UserIsOwnFamilyOrLeadershipTest, PackYearContextMixin, DetailView):
    """A family's own standing, read only."""

    template_name = "compliance/family_detail.html"
    context_object_name = "family"
    model = Family
    year_url_name = "compliance:family_detail_by_year"

    def get_year_url_kwargs(self):
        return {"pk": self.kwargs["pk"]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        family = self.object
        context.setdefault("family", family)

        if family is None:
            context["groups"] = []
            context["outstanding"] = []
            return context

        records = (
            RequirementRecord.objects.filter(family=family, year=context["years"]["viewing"])
            .select_related("requirement", "member")
            .order_by("requirement__sort_order", "requirement__name")
        )
        context["groups"] = self.group_by_subject(family, records)
        context["outstanding"] = [record for record in records if not record.is_satisfied]
        return context

    @staticmethod
    def group_by_subject(family, records):
        """
        One panel per person, plus one for the family as a whole, so a parent
        can see at a glance who still owes what.
        """
        by_member = {}
        household = []
        for record in records:
            if record.member_id:
                by_member.setdefault(record.member_id, []).append(record)
            else:
                household.append(record)

        groups = [{"subject": scout, "records": by_member.get(scout.pk, [])} for scout in family.children.all()]
        groups += [{"subject": adult, "records": by_member.get(adult.pk, [])} for adult in family.adults.all()]
        if household:
            groups.append({"subject": family, "records": household})
        return groups


class MyFamilyComplianceView(ActiveMemberOrContributorTest, FamilyComplianceView):
    """
    The signed in member's own family.

    ActiveMemberOrContributorTest is listed first so its test_func wins over
    the inherited ownership check, which would be redundant here.
    """

    year_url_name = "compliance:my_family_by_year"

    def get_year_url_kwargs(self):
        return {}

    def get_object(self, queryset=None):
        # Contributors and brand new signups have no family yet.
        return self.request.user.family
