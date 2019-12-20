import uuid
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ckeditor.fields import RichTextField

from address_book.models import Venue
from documents.models import Document


def get_pack_year(date_to_test=timezone.now()):
    """
    Given a date, calculate the date range (start, end) for the pack year which encapsulates that date.
    """
    pack_year_begins = datetime(date_to_test.year, settings.PACK_YEAR_BEGIN_MONTH, settings.PACK_YEAR_BEGIN_DAY)

    if pack_year_begins <= date_to_test < pack_year_begins.replace(year=pack_year_begins.year + 1):
        pack_year_begins = pack_year_begins.replace(year=pack_year_begins.year - 1)

    pack_year_ends = pack_year_begins.replace(year=pack_year_begins.year + 1) - timezone.timedelta(days=1)
    return pack_year_begins, pack_year_ends


class Category(models.Model):
    """
    Events should be tagged with a category for filtering and display on the website
    """
    # Define available colors for the category, mapped to Bootstrap text-colors
    # (https://getbootstrap.com/docs/4.4/utilities/colors/)
    BLUE = 'primary'
    GREEN = 'success'
    RED = 'danger'
    YELLOW = 'warning'
    AQUA = 'info'
    GREY = 'secondary'
    COLOR_CHOICES = (
        (BLUE, _('Blue')),
        (GREEN, _('Green')),
        (RED, _('Red')),
        (YELLOW, _('Yellow')),
        (AQUA, _('Light Blue')),
        (GREY, _('Grey/Muted')),
    )

    # Define available FontAwesome icons for the category
    # https://fontawesome.com/icons?d=gallery
    ALARM_CLOCK = '<i class="far fa-alarm-clock"></i>'
    AWARD = '<i class="fas fa-award"></i>'
    BELL = '<i class="far fa-bell"></i>'
    CAMPGROUND = '<i class="fas fa-campground"></i>'
    CALENDAR = '<i class="far fa-calendar-alt"></i>'
    DONATE = '<i class="fas fa-donate"></i>'
    GIFT = '<i class="fas fa-gift"></i>'
    SMALL_GROUP = '<i class="fas fa-user-friends"></i>'
    LARGE_GROUP = '<i class="fas fa-users"></i>'
    MEDAL = '<i class="fas fa-medal"></i>'
    HANDSHAKE = '<i class="fas fa-handshake"></i>'
    HELPING_HANDS = '<i class="fas fa-hands-helping"></i>'
    HEART = '<i class="fas fa-heart"></i>'
    RIBBON = '<i class="fas fa-ribbon"></i>'
    SEEDLING = '<i class="fas fa-seedling"></i>'
    STAR = '<i class="fas fa-star"></i>'
    ICON_CHOICES = (
        (ALARM_CLOCK, _('Alarm Clock')),
        (AWARD, _('Award')),
        (BELL, _('Bell')),
        (CALENDAR, _('Calendar')),
        (CAMPGROUND, _('Campground')),
        (DONATE, _('Donate')),
        (GIFT, _('Gift box')),
        (LARGE_GROUP, _('Group (large)')),
        (SMALL_GROUP, _('Group (small)')),
        (HELPING_HANDS, _('Hands helping')),
        (HANDSHAKE, _('Hands shaking')),
        (HEART, _('Heart')),
        (MEDAL, _('Medal')),
        (RIBBON, _('Ribbon')),
        (SEEDLING, _('Seedling')),
        (STAR, _('Star')),
    )

    name = models.CharField(max_length=32, help_text=_('e.g. Pack Meeting, Den Meeting, Campout, etc.'))
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text=_('Give a little more detail about the kinds of events in this category'))
    icon = models.CharField(max_length=64, choices=ICON_CHOICES, blank=True, null=True,
                            help_text=_('Optionally choose an icon to display with these events'))
    color = models.CharField(max_length=16, choices=COLOR_CHOICES, blank=True, null=True,
                             help_text=_('Optionally choose a color to display these event in.'))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        ordering = ('name',)
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name


class Event(models.Model):
    """
    Store information about events
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='events', blank=True, null=True)
    location = models.CharField(max_length=64, blank=True, null=True)

    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)

    description = RichTextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='events')
    attachments = models.ManyToManyField(Document, related_name='events', blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start']
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('event_detail', args=[str(self.id)])

    def get_location(self):
        if self.venue and self.location:
            return "{} ({})".format(self.venue, self.location)
        elif self.venue:
            return self.venue
        elif self.location:
            return self.location
        else:
            return _('TBD')

    get_location.short_description = _('Location')

    def clean(self):
        if self.end < self.start:
            raise ValidationError(_('Event cannot end before it starts.'))

    @property
    def pack_year(self):
        year = get_pack_year(self.start.date)
        return year

    @property
    def duration(self):
        """ Tells us how long the event is scheduled for """
        if self.start and self.end:
            return self.end - self.start
