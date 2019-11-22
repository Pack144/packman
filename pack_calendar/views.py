from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView

from membership.mixins import ActiveMemberOrContributorTestMixin

from .models import Event


class EventListView(ActiveMemberOrContributorTestMixin, ListView):
    """ Display a listing of all the events coming up """
    model = Event
    paginate_by = 10
    template_name = 'events/event_list.html'
    context_object_name = 'event_list'

    def get_queryset(self):
        """ Return a queryset containing all events for the next 6 months"""
        return Event.objects.filter(end__lte=timezone.now() + timezone.timedelta(weeks=26)).filter(end__gte=timezone.now())
