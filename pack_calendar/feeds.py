from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.html import strip_tags

from django_ical.views import ICalFeed

from .models import Event


try:
    site = Site.objects.get_current()
except:
    # It's ugly. It's here in case initial migrations haven't been performed yet and the sites database doesn't exist
    # Should only stick around until the initial migrations have been completed.
    site = Site(name='fake', domain='localhost')


class EventFeed(ICalFeed):
    """
    A simple event calendar feed
    """

    product_id = f'-//{site.domain}//django-ical/EN'
    title = site.name
    timezone = settings.TIME_ZONE
    file_name = 'calendar.ics'

    def items(self):
        return Event.objects.filter(published=True)

    def item_guid(self, item):
        return item.uuid
    
    def item_title(self, item):
        return item.name
    
    def item_description(self, item):
        return strip_tags(item.description) if item.description else None
    
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
