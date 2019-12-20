from django.views.generic import DetailView, ListView

from membership.mixins import ActiveMemberOrContributorTest

from .models import Den


class DenDetailView(ActiveMemberOrContributorTest, DetailView):
    model = Den
    paginate_by = 20


class DensListView(ActiveMemberOrContributorTest, ListView):
    model = Den
    paginate_by = 20
