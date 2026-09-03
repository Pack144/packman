from django.views.generic import DetailView, ListView

from packman.calendars.models import PackYear
from packman.committees.models import CommitteeMember
from packman.membership.mixins import ActiveMemberOrContributorTest

from .models import Den


class DenDetailView(ActiveMemberOrContributorTest, DetailView):
    model = Den
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = (
            PackYear.objects.get(year=PackYear.get_pack_year(self.kwargs["year"])["end_date"].year)
            if "year" in self.kwargs
            else PackYear.objects.current()
        )
        # TODO: Look into this. Maybe we want to search for den_memberships
        all_years = PackYear.objects.filter(committee_membership__den=context["den"]).distinct()
        context["current_year"] = year
        context["all_years"] = all_years
        context["leaders"] = CommitteeMember.objects.filter(
            den=context["den"],
            year=year,
        )
        context["cubs"] = self.get_cubs(context["den"])
        context["parents"] = self.get_parents(context["den"])
        return context

    @staticmethod
    def get_cubs(den):
        """Every active Cub in this den, each paired with their own parents."""
        rows = []
        for membership in den.active_cubs().select_related("scout__family"):
            scout = membership.scout
            parents = list(scout.family.adults.all()) if scout.family_id else []
            rows.append({"scout": scout, "parents": parents})
        return rows

    @staticmethod
    def get_parents(den):
        """
        Every parent with a Cub in this den, each paired with only the first
        names of their own Cub(s) who are in this den — never a sibling
        assigned to a different den.
        """
        parents = {}
        for membership in den.active_cubs().select_related("scout__family"):
            scout = membership.scout
            if not scout.family_id:
                continue
            for adult in scout.family.adults.all():
                parents.setdefault(adult, []).append(scout.short_name)
        return sorted(
            ({"adult": adult, "cubs": cubs} for adult, cubs in parents.items()),
            key=lambda entry: (entry["adult"].last_name, entry["adult"].get_short_name()),
        )


class DensListView(ActiveMemberOrContributorTest, ListView):
    model = Den
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        if "year" in self.kwargs:
            Den.objects.active_in(self.kwargs["year"])
        else:
            return queryset.current()
