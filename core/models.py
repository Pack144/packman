import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class UUIDModel(models.Model):
    """
    Abstract base model that relies on UUID rather than sequential numbers
    as the primary key
    """
    uuid = models.UUIDField(
        _('UUID'),
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides timestamps for created and updated as
    standard
    """
    date_added = models.DateTimeField(
        _('date added'),
        auto_now=True,
    )
    last_updated = models.DateTimeField(
        _('last updated'),
        auto_now=True,
    )

    class Meta:
        abstract = True


class TimeStampedUUIDModel(TimeStampedModel, UUIDModel):
    """
    Abstract base model that provides timestamps for created and updated as
    standard and also relies on UUID rather than sequential numbers as the
    primary key
    """

    class Meta:
        abstract = True
