from django.db.models import F
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from membership.mixins import ActiveMemberOrContributorTest
from pack_calendar.models import get_pack_year

from . import models


class CommitteesList(LoginRequiredMixin, generic.ListView):
    """
    Display a list of Committees with members assigned for any given year. If no year is supplied, then display the
    current committees list based on the Pack Year as defined in settings.py.
    """
    model = models.Committee
    paginate_by = 20
    template_name = 'committees/committees_list.html'

    def get_queryset(self):
        year = self.kwargs['year'] if 'year' in self.kwargs else get_pack_year()['end_date'].year
        return models.Committee.objects.filter(membership__year_served=year).distinct()


class CommitteeDetail(ActiveMemberOrContributorTest, generic.DetailView):
    model = models.Committee
    template_name = 'committees/committee_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.kwargs['year'] if 'year' in self.kwargs else get_pack_year()['end_date'].year
        context['members'] = models.Membership.objects.filter(committee=context['committee'], year_served=year)
        return context
