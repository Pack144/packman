import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from membership.models import AdultMember


class VenueType(models.Model):
    """
    Specifying a VenueType allows for sorting and filtering venues. Used by the cub sign-up view to provide a list of
    schools the pack is aware of.
    """
    type = models.CharField(max_length=16, help_text=_(
        "e.g. School, Campground, Park, etc."))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['type']
        verbose_name = _("Venue Type")
        verbose_name_plural = _("Venue Types")

    def __str__(self):
        return self.type


class Venue(models.Model):
    """
    Venues are locations where the pack may meet in the pack_caledar app and by ChildMembers to record the school they
    attend.
    """
    name = models.CharField(max_length=128, unique=True)
    type = models.ManyToManyField(VenueType, related_name='venues')
    url = models.URLField(_("Website"), blank=True, null=True)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def __str__(self):
        return self.name


class Address(models.Model):
    """
    Address object to store physical address information. Used by Adult members and Venues. When associated with a
    member, the published option controls whether the address will be displayed on a member's detail page. This setting
    is not honored for venues, as the address should always be visible.
    """
    HOME = 'H'
    WORK = 'W'
    OTHER = 'O'
    TYPE_CHOICES = (
        (HOME, _("Home")),
        (WORK, _("Work")),
        (OTHER, _("Other")),
    )
    street = models.CharField(_("Street"), max_length=128)
    street2 = models.CharField(_("Street"), max_length=128, blank=True, null=True)
    city = models.CharField(_("City"), max_length=64)
    state = USStateField(_("State"))
    zip_code = USZipCodeField(_("ZIP Code"))

    type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True, null=True)

    published = models.BooleanField(default=True, help_text=_(
        "Display this address to other members of the pack on the member details page."))

    member = models.ForeignKey('membership.AdultMember', on_delete=models.SET_NULL, related_name='addresses', blank=True, null=True)
    venue = models.OneToOneField(Venue, on_delete=models.SET_NULL, related_name='address', null=True, blank=True)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['street']
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        if self.member:
            return f'{self.member}: {self.single_line_display()}'
        else:
            return self.single_line_display()

    def single_line_display(self):
        if self.street2:
            return f'{self.street} {self.street2}, {self.city} {self.state}, {self.zip_code}'
        else:
            return f'{self.street}, {self.city} {self.state}, {self.zip_code}'


class PhoneNumber(models.Model):
    """
    Phone number object to store phone contact details. Used by Adult members and Venues. When associated with a
    member, the published option controls whether the number will be displayed on a member's detail page. This setting
    is not honored for venues, as the phone number should always be visible.
    """
    HOME = 'H'
    MOBILE = 'M'
    WORK = 'W'
    OTHER = 'O'
    TYPE_CHOICES = (
        (HOME, _("Home")),
        (MOBILE, _("Mobile")),
        (WORK, _("Work")),
        (OTHER, _("Other")),
    )
    number = PhoneNumberField(_("Phone Number"))
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True, null=True)
    published = models.BooleanField(default=True, help_text=_(
        "Display this phone number to other members of the pack in the member details page."))

    member = models.ForeignKey(AdultMember, on_delete=models.SET_NULL, related_name='phone_numbers', blank=True, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, related_name='phone_numbers', blank=True, null=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        verbose_name = _("Phone Number")
        verbose_name_plural = _("Phone Numbers")

    def __str__(self):
        return self.number.as_national
