from django.conf import settings
from django.utils.text import gettext_lazy as _

from django_ical.views import ICalFeed

from packman.membership.models import Family

from .models import Event


class EventFeed(ICalFeed):
    """
    A simple event calendar feed
    """

    product_id = f"-//{settings.PACK_NAME}//ical/EN"
    title = settings.PACK_SHORTNAME
    timezone = settings.TIME_ZONE

    def get_object(self, request, family_uuid):
        return Family.objects.get(uuid=family_uuid)

    def description(self, obj):
        return _(
            f"{settings.PACK_NAME} calendar of meetings, events, outings, and "
            f"campouts. Created specifically for the {obj.name}."
        )

    def file_name(self, obj):
        """Generate a unique calendar file per family."""
        return f"{obj.uuid}.ics"

    def items(self, obj):
        """
        Gather all calendar events applicable for the family. Based on the
        years a family has a Scout assigned to a Den.
        """
        published_events = (
            Event.objects.select_related("category").prefetch_related("venue", "venue__address").filter(published=True)
        )
        events_for_family = Event.objects.none()
        for year in obj.years_active():
            # Filter for events that occur within each Pack year
            events_in_year = published_events.filter(start__date__range=[year.start_date, year.end_date])
            events_for_family = events_for_family | events_in_year
        return events_for_family

    def item_guid(self, item):
        return item.uuid

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        return item.plain_text_description

    def item_start_datetime(self, item):
        return item.start

    def item_end_datetime(self, item):
        return item.end

    def item_created(self, item):
        return item.date_added

    def item_updateddate(self, item):
        return item.last_updated

    def item_location(self, item):
        return item.get_location_with_address()

    def item_status(self, item):
        return item.status

    def item_transparency(self, item):
        return "TRANSPARENT" if item.status == Event.CANCELLED else "OPAQUE"

    def item_categories(self, item):
        return (item.category.name,)
