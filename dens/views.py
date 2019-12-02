from django.views.generic import DetailView, ListView

from membership.mixins import ActiveMemberOrContributorTestMixin

from .models import Den


class DenDetailView(ActiveMemberOrContributorTestMixin, DetailView):
    model = Den


class DensListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Den
    paginate_by = 20
