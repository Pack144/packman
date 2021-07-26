from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import Http404
from django.utils.translation import gettext as _
from django.views.generic import DetailView

from .models import Message


class MessageDetailView(LoginRequiredMixin, DetailView):

    model = Message

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user and self.request.user not in obj.recipients:
            raise Http404(_("No %(verbose_name)s found matching the query") % {"verbose_name": queryset.model._meta.verbose_name})
        obj.mark_read(self.request.user)
        return obj
