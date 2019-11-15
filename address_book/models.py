from django.db import models

from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from events.models import Event
from membership.models import Member


class Address(models.Model):
    TYPE_CHOICES = (
        ('H', 'Home'),
        ('W', 'Work'),
        ('O', 'Other')
    )
    street = models.CharField(max_length=128)
    street2 = models.CharField(max_length=128, null=True, blank=True)
    city = models.CharField(max_length=64)
    state = USStateField()
    zip_code = USZipCodeField()

    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default='O')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='addresses', blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='addresses', blank=True, null=True)

    published = models.BooleanField(default=True, help_text='Display your address to other members of the pack.')

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'addresses'

    def __str__(self):
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
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default='O')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='phone_numbers', blank=True, null=True)

    published = models.BooleanField(default=True, help_text='Display this phone number to other members of the pack.')

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.number.as_national
