from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from packman.membership.mixins import ActiveMemberOrContributorTest

from .forms import EventForm
from .models import Event


class EventListView(ActiveMemberOrContributorTest, ListView):
    """
    Display a listing of all the events coming up
    """

    model = Event
    paginate_by = 10
    context_object_name = "events"

    def get_queryset(self):
        """
        Return a queryset containing all events for the next 6 months
        """
        return (
            Event.objects.filter(
                start__lte=timezone.now() + timezone.timedelta(weeks=26)
            )
            .filter(start__gte=timezone.now() - timezone.timedelta(hours=8))
            .order_by("start")
        )


class EventArchiveView(ActiveMemberOrContributorTest, ListView):
    """
    Display a list of past events
    """

    model = Event
    paginate_by = 10
    context_object_name = "events"
    template_name = "calendars/event_archive.html"

    def get_queryset(self):
        """
        Return a queryset containing all events for the next 6 months
        """
        return Event.objects.filter(start__lt=timezone.now())


class EventDetailView(ActiveMemberOrContributorTest, DetailView):
    """
    Display the details of a specific event
    """

    model = Event


class EventCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = EventForm
    model = Event
    permission_required = "calendars.add_event"
    success_message = _("The event %(name)s has been successfully created")


class EventUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = EventForm
    model = Event
    permission_required = "calendars.change_event"
    success_message = _("The event %(name)s has been successfully updated")


class EventDeleteView(PermissionRequiredMixin, DeleteView):
    model = Event
    permission_required = "calendars.delete_event"
    success_url = reverse_lazy("calendars:list")

    def delete(self, request, *args, **kwargs):
        success_message = _(
            "The event '%(event)s' has been successfully deleted."
        ) % {"event": self.get_object()}
        messages.success(request, success_message, "danger")
        return super().delete(request, *args, **kwargs)
