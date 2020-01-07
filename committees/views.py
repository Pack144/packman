from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.utils.translation import ugettext_lazy as _

from membership.mixins import ActiveMemberOrContributorTest

from . import models


class CommitteesList(LoginRequiredMixin, generic.ListView):
    model = models.Committee
    paginate_by = 20
    template_name = 'committees/committees_list.html'


class CommitteeDetail(ActiveMemberOrContributorTest, generic.DetailView):
    model = models.Committee
    template_name = 'committees/committee_detail.html'
