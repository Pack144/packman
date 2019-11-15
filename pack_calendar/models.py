import uuid
from datetime import datetime
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from address_book.models import Venue


def get_pack_year(date=timezone.now()):
    """ Given a date, calculate the date range (start, end) for the pack year which encapsulates that date. """
    start_str = '{} {}'.format(settings.PACK_YEAR_BEGIN_DATE, date.year)
    start = datetime.date(datetime.strptime(start_str, "%B %d %Y"))

    if start <= date.date() < start.replace(year=start.year + 1):
        date = date.replace(year=date.year - 1)
        start_str = '{} {}'.format(settings.PACK_YEAR_BEGIN_DATE, date.year)
        start = datetime.date(datetime.strptime(start_str, "%B %d %Y"))

    end = start.replace(year=start.year + 1) - timezone.timedelta(days=1)
    return start, end


class Category(models.Model):
    name = models.CharField(max_length=32, help_text=_('e.g. Pack Meeting, Den Meeting, Campout, etc.'))
    description = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=32)
    location = models.CharField(max_length=64, blank=True, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='event', blank=True, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start']
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('event_detail', args=[str(self.id)])

    def get_location(self):
        if self.venue:
            return self.venue
        elif self.location:
            return self.location
        else:
            return None

    get_location.short_description = _('Location')

    def pack_year(self):
        year = get_pack_year(self.start).end.year
        return year
