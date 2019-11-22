from django.views.generic import CreateView, DetailView, UpdateView, ListView

from membership.mixins import ActiveMemberOrContributorTestMixin

from .models import Category, Document


class DocumentListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Document

    def get_context_data(self, **kwargs):
        context = super(DocumentListView, self).get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
