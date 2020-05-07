import html as python_html
import uuid

from datetime import datetime

from tinymce.models import HTMLField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import html, timezone
from django.utils.translation import gettext_lazy as _


class PackYear(models.Model):
    """
    Stores the start and end date of a pack year in the database. Used by
    committee assignments, den assignments, and events to keep things sorted.
    """
    year = models.PositiveSmallIntegerField(
        primary_key=True,
    )

    class Meta:
        indexes = [models.Index(fields=['year'])]
        ordering = ('-year',)
        verbose_name = _("Pack Year")
        verbose_name_plural = _("Pack Years")

    def __str__(self):
        if self.start_date.year == self.end_date.year:
            return self.start_date.year
        else:
            return f"{self.start_date.year} - {self.end_date.year}"

    @staticmethod
    def get_pack_year(date_to_test=timezone.now()):
        """
        Given a date, calculate the date range (start, end) for the pack year
        which encapsulates that date.
        """
        if not isinstance(date_to_test, datetime):
            date_to_test = timezone.datetime(date_to_test, 1, 1)
        if timezone.is_aware(date_to_test):
            date_to_test = timezone.make_naive(date_to_test)
        pack_year_begins = datetime(
            date_to_test.year,
            settings.PACK_YEAR_BEGIN_MONTH,
            settings.PACK_YEAR_BEGIN_DAY
        )

        if not pack_year_begins <= date_to_test < pack_year_begins.replace(
                year=pack_year_begins.year + 1
        ):
            pack_year_begins = pack_year_begins.replace(
                year=pack_year_begins.year - 1
            )

        pack_year_ends = pack_year_begins.replace(
            year=pack_year_begins.year + 1
        ) - timezone.timedelta(seconds=1)
        return {'start_date': pack_year_begins, 'end_date': pack_year_ends}

    @staticmethod
    def get_current_pack_year():
        year, created = PackYear.objects.get_or_create(
            year=PackYear.get_pack_year()['end_date'].year
        )
        return year

    @staticmethod
    def get_current_pack_year_year():
        year_obj = PackYear.get_current_pack_year()
        return year_obj.end_date.year

    @property
    def start_date(self):
        # Calculate the start date of the pack year
        return self.get_pack_year(self.year)['start_date']

    @property
    def end_date(self):
        # Calculate the end date of the pack year
        return self.get_pack_year(self.year)['end_date']


class Category(models.Model):
    """
    Events should be tagged with a category for filtering and display
    """
    # Define available colors for the category, mapped to Bootstrap text-colors
    # (https://getbootstrap.com/docs/4.4/utilities/colors/)
    BLUE = 'primary'
    GREEN = 'success'
    RED = 'danger'
    YELLOW = 'warning'
    TEAL = 'info'
    GREY = 'secondary'
    TRANSPARENT = 'transparent'
    LIGHT = 'light'
    DARK = 'dark'
    WHITE = 'white'
    COLOR_CHOICES = (
        (BLUE, _("Blue")),
        (GREEN, _("Green")),
        (RED, _("Red")),
        (YELLOW, _("Yellow")),
        (TEAL, _("Teal")),
        (GREY, _("Grey/Muted")),
        (TRANSPARENT, _("Transparent"))
    )

    # Define available FontAwesome icons for the category
    # https://fontawesome.com/icons?d=gallery
    ALARM_CLOCK = '<i class="far fa-alarm-clock"></i>'
    AWARD = '<i class="fas fa-award"></i>'
    BELL = '<i class="far fa-bell"></i>'
    CAMPGROUND = '<i class="fas fa-campground"></i>'
    CALENDAR = '<i class="far fa-calendar-alt"></i>'
    CIRCLED_X = '<i class="far fa-times-circle"></i>'
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
        (ALARM_CLOCK, _("Alarm Clock")),
        (AWARD, _("Award")),
        (BELL, _("Bell")),
        (CALENDAR, _("Calendar")),
        (CAMPGROUND, _("Campground")),
        (CIRCLED_X, _("Circled 'X'")),
        (DONATE, _("Donate")),
        (GIFT, _("Gift box")),
        (LARGE_GROUP, _("Group (large)")),
        (SMALL_GROUP, _("Group (small)")),
        (HELPING_HANDS, _("Hands Helping")),
        (HANDSHAKE, _("Hands Shaking")),
        (HEART, _("Heart")),
        (MEDAL, _("Medal")),
        (RIBBON, _("Ribbon")),
        (SEEDLING, _("Seedling")),
        (STAR, _("Star")),
    )

    name = models.CharField(
        max_length=32,
        help_text=_("e.g. Pack Meeting, Den Meeting, Camp out, etc."),
    )
    description = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text=_(
            "Give a little more detail about the kinds of events in this "
            "category"),
    )
    icon = models.CharField(
        max_length=64,
        choices=ICON_CHOICES,
        blank=True,
        null=True,
        help_text=_("Optionally choose an icon to display with these events"),
    )
    color = models.CharField(
        max_length=16,
        choices=COLOR_CHOICES,
        blank=True,
        null=True,
        help_text=_("Optionally choose a color to display these event in."),
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [models.Index(fields=['name'])]
        ordering = ('name',)
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Event(models.Model):
    """ Store information about events """

    TENTATIVE = 'TENTATIVE'
    CONFIRMED = 'CONFIRMED'
    CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (TENTATIVE, _("Tentative")),
        (CONFIRMED, _("Confirmed")),
        (CANCELLED, _("Cancelled")),
    )

    name = models.CharField(
        max_length=64,
    )
    venue = models.ForeignKey(
        'address_book.Venue',
        on_delete=models.CASCADE,
        related_name='events',
        blank=True,
        null=True,
    )
    location = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    start = models.DateTimeField()
    end = models.DateTimeField(
        blank=True,
        null=True,
    )

    description = HTMLField(
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='events',
    )
    attendees = models.ManyToManyField(
        'membership.Adult',
        blank=True,
    )
    attendee_groups = models.ManyToManyField(
        'post_office.GroupMailbox',
        blank=True,
    )
    attachments = models.ManyToManyField(
        'documents.Document',
        related_name='events',
        blank=True
    )
    published = models.BooleanField(
        _("Show on iCal"),
        default=True,
    )
    status = models.CharField(
        max_length=9,
        choices=STATUS_CHOICES,
        default=CONFIRMED,
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [models.Index(
            fields=['name', 'venue', 'location', 'start', 'end', 'category']
        )]
        ordering = ['-start']
        verbose_name = _("Event")
        verbose_name_plural = _("Events")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('event_detail', args=[str(self.uuid)])

    def get_location(self):
        if self.venue and self.location:
            return f"{self.venue} ({self.location})"
        elif self.venue:
            return self.venue
        elif self.location:
            return self.location
        else:
            return ""

    def get_location_with_address(self):
        if hasattr(self.venue, 'address'):
            return f"{self.get_location()}\n{self.venue.address}"
        else:
            return self.get_location()

    get_location.short_description = _("Location")

    def clean(self):
        """ Verify that end datetime is not before the start datetime. """
        if self.end and self.end <= self.start:
            raise ValidationError(_("Event cannot end before it starts."))

    @property
    def pack_year(self):
        year = PackYear.get_pack_year(self.start.date)
        return year

    @property
    def duration(self):
        """ Calculate how long the event is scheduled for """
        if self.start and self.end:
            return self.end - self.start

    @property
    def plain_text_description(self):
        return python_html.unescape(html.strip_tags(self.description))

    def get_attendee_list(self):
        attendee_list = list()
        if self.attendees.count():
            for attendee in self.attendees_set:
                attendee_list.append(attendee)
        if self.attendee_groups.count():
            for attendee in self.attendee_groups.all():
                attendee_list.append(attendee)
        return attendee_list
