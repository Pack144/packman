from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from .models import Document


class DocumentListView(ListView):
    model = Document
