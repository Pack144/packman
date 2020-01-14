from django.conf import settings

from django_ical.views import ICalFeed

from .models import Event


class EventFeed(ICalFeed):
    """
    A simple event calendar feed
    """

    product_id = '-//dev.pack144.org//Example/EN'
    timezone = settings.TIME_ZONE
    file_name = 'event.ics'

    def items(self):
        return Event.objects.all()
    
    def item_title(self, item):
        return item.name
    
    def item_description(self, item):
        return item.description
    
    def item_start_datetime(self, item):
        return item.start
    
    def item_end_datetime(self, item):
        return item.end
    
    def item_created(self, item):
        return item.date_added
    
    def item_updateddate(self, item):
        return item.last_updated
    
    def item_location(self, item):
        return item.get_location()
