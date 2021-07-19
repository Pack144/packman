from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import generic

from packman.membership.mixins import ActiveMemberOrContributorTest

from .forms import EventForm
from .models import Event, PackYear


class EventListView(ActiveMemberOrContributorTest, generic.ListView):
    """
    Display a listing of all the events coming up
    """

    model = Event
    paginate_by = 10
    context_object_name = "events"

    def get_queryset(self):
        """
        Return a queryset containing all future events for the current Pack Year
        """
        return (
            Event.objects.filter(start__lte=PackYear.objects.current().end_date)
            .filter(start__gte=timezone.now() - timezone.timedelta(hours=8))
            .order_by("start")
        )


class EventArchiveView(ActiveMemberOrContributorTest, generic.ListView):
    """
    Display a list of past events
    """

    model = Event
    paginate_by = 10
    context_object_name = "events"
    template_name = "calendars/event_archive.html"

    def get_queryset(self):
        """
        Return a queryset containing all previous events
        """
        return Event.objects.filter(start__lt=timezone.now())


class EventDetailView(ActiveMemberOrContributorTest, generic.DetailView):
    """
    Display the details of a specific event
    """

    model = Event


class EventCreateView(PermissionRequiredMixin, SuccessMessageMixin, generic.CreateView):
    form_class = EventForm
    model = Event
    permission_required = "calendars.add_event"
    success_message = _("The event %(name)s has been successfully created")


class EventUpdateView(PermissionRequiredMixin, SuccessMessageMixin, generic.UpdateView):
    form_class = EventForm
    model = Event
    permission_required = "calendars.change_event"
    success_message = _("The event %(name)s has been successfully updated")


class EventDeleteView(PermissionRequiredMixin, generic.DeleteView):
    model = Event
    permission_required = "calendars.delete_event"
    success_url = reverse_lazy("calendars:list")

    def delete(self, request, *args, **kwargs):
        success_message = _("The event '%(event)s' has been successfully deleted.") % {"event": self.get_object()}
        messages.success(request, success_message, "danger")
        return super().delete(request, *args, **kwargs)
