from django.db import models
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from core.models import TimeStampedUUIDModel
from membership.models import Adult, Family
from calendars.models import PackYear
from committees.models import Committee
from dens.models import Den


class Category(TimeStampedUUIDModel):
    """
    Specifying a Category allows for sorting and filtering venues. Used by the
    cub sign-up view to provide a list of schools the pack is aware of.
    """
    name = models.CharField(
        max_length=64,
        help_text=_("e.g. School, Campground, Park, etc.")
    )

    class Meta:
        ordering = ['name']
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        return self.name


class Venue(TimeStampedUUIDModel):
    """
    Venues are locations where the pack may meet in the calendars app and
    by Scouts to record the school they attend.
    """
    name = models.CharField(
        max_length=128,
        unique=True
    )
    categories = models.ManyToManyField(
        Category,
        related_name='venues'
    )
    url = models.URLField(
        _("Website"),
        blank=True,
        default="",
    )

    class Meta:
        ordering = ['name']
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def __str__(self):
        return self.name


class Address(TimeStampedUUIDModel):
    """
    Address object to store physical address information. Used by Adult members
    and Venues. When associated with a member, the published option controls
    whether the address will be displayed on a member's detail page. This
    setting is ignored for venues, as the address should always be visible.
    """
    HOME = 'H'
    WORK = 'W'
    OTHER = 'O'
    TYPE_CHOICES = (
        (HOME, _("Home")),
        (WORK, _("Work")),
        (OTHER, _("Other")),
        (None, _("Type")),
    )

    street = models.CharField(
        _("Address"),
        max_length=128,
    )
    street2 = models.CharField(
        _("Unit / Apartment / Suite"),
        max_length=128,
        blank=True,
        default="",
    )
    city = models.CharField(
        _("City"),
        max_length=64,
    )
    state = USStateField(
        _("State"),
    )
    zip_code = USZipCodeField(
        _("ZIP Code"),
    )
    type = models.CharField(
        max_length=1,
        choices=TYPE_CHOICES,
        blank=True,
        default="",
    )
    published = models.BooleanField(
        default=True,
        help_text=_("Display this address to other members of the pack."),
    )

    # Related models
    member = models.ForeignKey(
        Adult,
        on_delete=models.SET_NULL,
        related_name='addresses',
        blank=True,
        null=True,
    )
    venue = models.OneToOneField(
        Venue,
        on_delete=models.SET_NULL,
        related_name='address',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['street']
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        if self.member:
            return f"{self.member}: {self.single_line_display()}"
        else:
            return self.single_line_display()

    def single_line_display(self):
        if self.street2:
            return f"{self.street} " \
                   f"{self.street2}, " \
                   f"{self.city}, " \
                   f"{self.state} " \
                   f"{self.zip_code}"
        else:
            return f"{self.street}, " \
                   f"{self.city}, " \
                   f"{self.state} " \
                   f"{self.zip_code}"


class PhoneNumber(TimeStampedUUIDModel):
    """
    Phone number object to store phone contact details. Used by Adult members
    and Venues. When associated with a member, the published option controls
    whether the number will be displayed on a member's detail page. This
    setting is ignored for venues, as the number should always be visible.
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
        (None, _("Type")),
    )

    number = PhoneNumberField(
        _("Phone Number"),
        region='US',
    )
    type = models.CharField(
        max_length=1,
        choices=TYPE_CHOICES,
        blank=True,
        default="",
    )
    published = models.BooleanField(
        default=True,
        help_text=_("Display this phone number to other members of the pack."),
    )
    member = models.ForeignKey(
        Adult,
        on_delete=models.SET_NULL,
        related_name='phone_numbers',
        blank=True,
        null=True,
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.SET_NULL,
        related_name='phone_numbers',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['number']
        verbose_name = _("Phone Number")
        verbose_name_plural = _("Phone Numbers")

    def __str__(self):
        return self.number.as_national


class DistributionList(TimeStampedUUIDModel):
    name = models.CharField(_("name"), max_length=128)
    email = models.EmailField(_("email address"), unique=True)

    is_all = models.BooleanField(_("all active members"), default=False)
    committees = models.ManyToManyField(Committee, related_name="distribution_lists", blank=True)
    dens = models.ManyToManyField(Den, related_name="distribution_lists", blank=True)

    contact_us = models.BooleanField(
        _("listed on contact us page"),
        default=False,
    )

    class Meta:
        verbose_name = _("distribution list")
        verbose_name_plural = _("distribution lists")

    def __str__(self):
        return self.name

    def get_email_addresses(self):
        return [
            (" ".join((n or f, l)), e) for f, n, l, e in self.get_members().values_list("first_name", "nickname", "last_name", "email")
        ]

    def get_members(self):
        if self.is_all:
            return Adult.objects.filter(family__in=Family.objects.active())
        else:
            return Adult.objects.filter(
                Q(
                    family__in=Family.objects.active().filter(
                        children__den_memberships__den__in=self.dens.all(),
                        children__den_memberships__year_assigned=PackYear.objects.current(),
                    )
                )
                | Q(
                    family__in=Family.objects.active(),
                    committee_memberships__committee__in=self.committees.all(),
                    committee_memberships__year_assigned=PackYear.objects.current(),
                )
            )

    @cached_property
    def email_address(self):
        return self.get_email_addresses()

    @cached_property
    def members(self):
        return self.get_members()
