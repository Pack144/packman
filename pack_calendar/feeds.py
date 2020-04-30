from icalendar import vCalAddress, vText

from django.conf import settings
from django.utils.text import gettext_lazy as _

from bs4 import BeautifulSoup
from django_ical.views import ICalFeed

from membership.models import Family
from .models import Event


class EventFeed(ICalFeed):
    """
    A simple event calendar feed
    """

    product_id = f"-//{settings.PACK_NAME}//ical/EN"
    title = settings.PACK_NAME
    timezone = settings.TIME_ZONE
    description = _(
        f"{settings.PACK_NAME} calendar of meetings, events, outings, and "
        f"campouts."
    )

    def get_object(self, request, family_uuid):
        return Family.objects.get(uuid=family_uuid)

    def file_name(self, obj):
        return f'{obj.uuid}.ics'

    def items(self, obj):
        return Event.objects.filter(published=True)

    def item_guid(self, item):
        return item.uuid

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        return BeautifulSoup(
            item.description, 'html.parser'
        ).text if item.description else None

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
        if item.status == 'CANCELED':
            return 'TRANSPARENT'
        else:
            return 'OPAQUE'

    def item_categories(self, item):
        return (item.category, )

    def item_attendee(self, item):
        if item.get_attendee_list().count:
            attendees = []
            for a in item.get_attendee_list():
                attendee = vCalAddress('MAILTO:pack@pack144.org')
                attendee.params['cn'] = vText('All Pack 144')
                attendees.append(attendee)
            return attendees
