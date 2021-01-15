from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic

from packman.membership.mixins import ActiveMemberOrContributorTest
from packman.calendars.models import PackYear
from . import models


class CommitteesList(LoginRequiredMixin, generic.ListView):
    """
    Display a list of Committees with members assigned for any given year. If
    no year is supplied, then display the current committees list based on the
    Pack Year as defined in settings.py.
    """
    model = models.Committee
    paginate_by = 50
    template_name = 'committees/committees_list.html'

    def get_queryset(self):
        year = PackYear.objects.get(
            year=PackYear.get_pack_year(self.kwargs['year'])['end_date'].year
        ) if 'year' in self.kwargs else PackYear.get_current_pack_year()
        return models.Committee.objects.filter(
            membership__year_served=year
        ).distinct()


class CommitteeDetail(ActiveMemberOrContributorTest, generic.DetailView):
    model = models.Committee
    template_name = 'committees/committee_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = PackYear.objects.get(
            year=PackYear.get_pack_year(self.kwargs['year'])['end_date'].year
        ) if 'year' in self.kwargs else PackYear.get_current_pack_year()
        all_years = PackYear.objects.filter(
            committee_memberships__committee=context['committee']).distinct()
        context['current_year'] = year
        context['all_years'] = all_years
        context['members'] = models.Membership.objects.filter(
            committee=context['committee'],
            year_served=year,
            position__lt=models.Membership.AKELA,
        )
        context['akelas'] = models.Membership.objects.filter(
            committee=context['committee'],
            year_served=year,
            position__gte=models.Membership.AKELA,
        )
        return context
