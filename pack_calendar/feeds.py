from django.conf import settings

from bs4 import BeautifulSoup
from django_ical.views import ICalFeed

from .models import Event


class EventFeed(ICalFeed):
    """
    A simple event calendar feed
    """

    product_id = f"-//{settings.PACK_NAME}//ical/EN"
    title = settings.PACK_NAME
    timezone = settings.TIME_ZONE
    description = f"{settings.PACK_NAME} calendar of meetings, events, outings, and campouts."
    file_name = 'calendar.ics'
    method = 'PUBLISH'

    def items(self):
        return Event.objects.filter(published=True)

    def item_guid(self, item):
        return item.uuid
    
    def item_title(self, item):
        return item.name
    
    def item_description(self, item):
        return BeautifulSoup(item.description, 'html.parser').text if item.description else None
    
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

    def item_categories(self, item):
        return (item.category, )
