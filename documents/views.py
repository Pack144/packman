from django.db.models import Prefetch
from django.views.generic import ListView

from membership.mixins import ActiveMemberOrContributorTestMixin

from .models import Category, Document


class DocumentListView(ActiveMemberOrContributorTestMixin, ListView):
    """ Display a listing of all the documents published to the repository """
    model = Document
    template_name = 'documents/document_list.html'

    def get_queryset(self):
        """ Provide Category data and filter based on whether document should be displayed """
        return Category.objects.prefetch_related(Prefetch('documents',
                                                          queryset=Document.objects.filter(display_in_repository=True)))
