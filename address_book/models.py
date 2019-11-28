from django.db import models
from django.utils.translation import gettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from membership.models import Member


class Address(models.Model):
    TYPE_CHOICES = (
        ('H', 'Home'),
        ('W', 'Work'),
        ('O', 'Other')
    )
    street = models.CharField(max_length=128)
    street2 = models.CharField(max_length=128, blank=True, null=True)
    city = models.CharField(max_length=64)
    state = USStateField()
    zip_code = USZipCodeField()

    type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True, null=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='addresses', blank=True, null=True)

    published = models.BooleanField(default=True, help_text=_('Display your address to other members of the pack.'))

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')

    def __str__(self):
        if self.member:
            return '{}: {}'.format(self.member.full_name(), self.single_line_display())
        else:
            return self.single_line_display()

    def single_line_display(self):
        if self.street2:
            return '{} {}, {} {}, {}'.format(self.street, self.street2, self.city, self.state, self.zip_code)
        else:
            return '{}, {} {}, {}'.format(self.street, self.city, self.state, self.zip_code)


class PhoneNumber(models.Model):
    TYPE_CHOICES = (
        ('H', 'Home'),
        ('M', 'Mobile'),
        ('W', 'Work'),
        ('O', 'Other')
    )
    number = PhoneNumberField()
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True, null=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='phone_numbers', blank=True, null=True)

    published = models.BooleanField(default=True, help_text='Display this phone number to other members of the pack.')

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        verbose_name = _('Phone Number')
        verbose_name_plural = _('Phone Numbers')

    def __str__(self):
        return self.number.as_national


class VenueType(models.Model):
    type = models.CharField(max_length=16, help_text='e.g. School, Campground, Park, etc.')

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['type']
        verbose_name = _('Venue Type')
        verbose_name_plural = _('Venue Types')

    def __str__(self):
        return self.type


class Venue(models.Model):
    name = models.CharField(max_length=128, unique=True)
    type = models.ForeignKey(VenueType, on_delete=models.CASCADE, related_name='venue')
    address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name='venue', null=True, blank=True,
                                   limit_choices_to={'member': None})
    phone_number = models.OneToOneField(PhoneNumber, on_delete=models.CASCADE, related_name='venue', null=True,
                                        blank=True, limit_choices_to={'member': None})

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Venue')
        verbose_name_plural = _('Venues')

    def __str__(self):
        return self.name
