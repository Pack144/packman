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
            else PackYear.get_current_pack_year()
        )
        # TODO: Look into this. Maybe we want to search for den_memberships
        all_years = PackYear.objects.filter(committee_membership__den=context["den"]).distinct()
        context["current_year"] = year
        context["all_years"] = all_years
        context["leaders"] = CommitteeMember.objects.filter(
            den=context["den"],
            year=year,
        )
        return context


class DensListView(ActiveMemberOrContributorTest, ListView):
    model = Den
    paginate_by = 20

    def get_queryset(self):
        return Den.objects.filter(scouts__year_assigned=PackYear.objects.current()).distinct()
