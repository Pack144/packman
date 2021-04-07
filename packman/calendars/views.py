from django.utils import timezone
from django.views.generic import DetailView, ListView

from packman.membership.mixins import ActiveMemberOrContributorTest
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


class EventDetailView(ActiveMemberOrContributorTest, DetailView):
    """
    Display the details of a specific event
    """

    model = Event


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
