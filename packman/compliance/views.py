from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView

from packman.committees.leadership import led_dens
from packman.dens.models import Den
from packman.membership.mixins import ActiveMemberOrContributorTest
from packman.membership.models import Family

from .mixins import PackYearContextMixin, UserIsOwnFamilyOrLeadershipTest, UserLeadsADenTest
from .models import Requirement, RequirementRecord
from .scouting_membership import summarize_active_cubs
from .summaries import summarize_den, summarize_family


class RequirementRollupMixin:
    """
    Counts each requirement's standing for a pack year in a single query.

    Follows the DenQuerySet.counting_members() idiom -- one annotate with
    filtered Counts -- rather than looping and querying per requirement.
    """

    def get_requirement_rollup(self, year):
        in_year = Q(record__year=year)

        return (
            Requirement.objects.active()
            .annotate(
                total=Count("record", filter=in_year, distinct=True),
                complete=Count(
                    "record", filter=in_year & Q(record__status=RequirementRecord.Status.COMPLETE), distinct=True
                ),
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
        context["families"] = self.get_matrix(year, requirements)
        context["filter"] = self.request.GET.get("filter", "")
        context["den"] = self.request.GET.get("den", "")
        # Registrations are not tracked as a Requirement; they are read off the
        # Cubs themselves. See compliance.scouting_membership for why.
        context["scouting_membership"] = summarize_active_cubs(year)
        return context

    def get_matrix(self, year, requirements):
        """
        A family-by-requirement grid, and how many families are square.

        Three queries: the rollup above, one aggregate over every record in the
        year, and one for the families. Deliberately not the per-row query loop
        that campaigns' OrderLeaderboardView uses.

        The counts are taken before the ``filter`` query parameter is applied,
        so the header still says how many families are outstanding out of the
        whole pack while the table below shows only those.
        """
        cells = {
            (row["family_id"], row["requirement_id"]): row
            for row in RequirementRecord.objects.filter(year=year, family__isnull=False)
            .values("family_id", "requirement_id")
            .annotate(
                total=Count("pk"),
                outstanding=Count("pk", filter=Q(status=RequirementRecord.Status.NOT_STARTED)),
            )
        }

        families = Family.objects.filter(pk__in=Family.objects.active_in(year).values("pk")).order_by("name")
        if den := self.request.GET.get("den"):
            families = families.filter(children__den_memberships__den__number=den).distinct()

        for cell in cells.values():
            cell["state"] = self.cell_state(cell)

        wanted = self.request.GET.get("filter")
        rows = []
        total = outstanding = 0
        for family in families:
            cell_row = [cells.get((family.pk, requirement.pk)) for requirement in requirements]
            total += 1
            if self.row_matches(cell_row, "outstanding"):
                outstanding += 1
            if wanted and not self.row_matches(cell_row, wanted):
                continue
            rows.append({"family": family, "cells": cell_row})

        return {
            "rows": rows,
            "total": total,
            "outstanding": outstanding,
            "complete": total - outstanding,
        }

    @staticmethod
    def cell_state(cell):
        """
        The single thing a family's cell should report.

        Partly done reads differently from nothing started: a family where one
        parent has filed a medical form and the other has not should not look
        the same as a family where neither has.
        """
        if cell["outstanding"]:
            return "partial" if cell["outstanding"] < cell["total"] else "outstanding"
        return "complete"

    @staticmethod
    def row_matches(cells, wanted):
        if wanted != "outstanding":
            return True
        # A partly done family still has outstanding items, so it keeps
        # matching the outstanding filter.
        return any(cell and cell[wanted] for cell in cells)


class DenComplianceDashboardView(UserLeadsADenTest, PackYearContextMixin, TemplateView):
    """
    Where a den leader sees who in their den still owes what.

    The pack dashboard's counterpart, narrowed to one den and read only. It
    reads the same records through the same summaries the family page uses, so
    a leader and a parent are never shown a different answer.
    """

    template_name = "compliance/den_dashboard.html"
    year_url_name = "compliance:den_dashboard_by_year"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = context["years"]["viewing"]

        available = list(self.get_available_dens(year))
        context["available_dens"] = available
        den = self.get_den(available)
        context["den"] = den

        if den is None:
            # A leader who held no den in the year they switched to. Not a
            # permission problem -- they may still switch back.
            return context

        summary = summarize_den(den, year)
        context["summary"] = summary
        context["rows"] = summary["rows"]
        context["requirements"] = summary["requirements"]
        context["outstanding"] = summary["outstanding"]
        # Registrations are not tracked as a Requirement; they are read off the
        # Cubs themselves. See compliance.scouting_membership for why.
        context["scouting_membership"] = summarize_active_cubs(year, cubs=summary["cubs"])
        return context

    def get_available_dens(self, year):
        """
        The dens this viewer may choose between for the year being viewed.

        Pack leadership already sees every family on the pack dashboard, so
        letting them pick any den here reveals nothing new and saves them
        needing a den assignment to use the page at all.
        """
        if self.request.user.has_perm("compliance.view_all_records"):
            return Den.objects.active_in(year).order_by("number")
        return led_dens(self.request.user, year)

    def get_den(self, available):
        """
        The selected den, or None when the viewer led none this year.

        A ``den`` that is not on the viewer's own list is a 404 rather than a
        quiet fall back to their first den: this query parameter is the whole
        authorization boundary, and a silent redirect would make an attempt to
        cross it look like it had worked.
        """
        wanted = self.request.GET.get("den")
        if not wanted:
            return available[0] if available else None
        try:
            return next(den for den in available if str(den.number) == wanted)
        except StopIteration:
            raise Http404(_("You do not lead that den."))


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

        summary = summarize_family(family, context["years"]["viewing"])
        context["groups"] = summary["groups"]
        context["outstanding"] = summary["outstanding"]
        context["registrations_due"] = summary["registrations_due"]
        context["needs_attention"] = summary["needs_attention"]
        return context


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
