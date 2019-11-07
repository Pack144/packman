import uuid

from django.db import models

from address_book.models import Address


class Event(models.Model):
    CATEGORY_CHOICES = (
        ('PACK', 'Pack Meeting'),
        ('DEN', 'Den Meeting'),
        ('CAMP', 'Campout'),
        ('SERVICE', 'Community Service'),
        ('LEADERS', 'Leadership'),
        ('SOCIAL', 'Social'),
        ('RECRUITING', 'Membership Drive'),
        ('OTHER', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=32)
    event_location = models.CharField(max_length=64, blank=True, null=True)
    address = models.OneToOneField(Address, on_delete=models.CASCADE, blank=True, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default='PACK')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def location(self):
        if self.address:
            return self.address
        elif self.event_location:
            return self.event_location
        else:
            return None
