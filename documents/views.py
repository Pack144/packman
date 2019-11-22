from django.views.generic import CreateView, DetailView, UpdateView, ListView

from membership.mixins import ActiveMemberOrContributorTestMixin

from .models import Document


class DocumentListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Document
