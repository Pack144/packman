import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class UUIDModel(models.Model):
    """
    Abstract base model that relies on UUID rather than sequential numbers
    as the primary key.
    """

    uuid = models.UUIDField(
        _("UUID"),
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides timestamps for created and updated as
    standard.
    """

    date_added = models.DateTimeField(
        _("created"), auto_now_add=True, help_text=_("Date and time this entry was first added to the database.")
    )
    last_updated = models.DateTimeField(
        _("modified"), auto_now=True, help_text=_("Date and time this entry was last changed in the database.")
    )

    class Meta:
        abstract = True


class TimeStampedUUIDModel(TimeStampedModel, UUIDModel):
    """
    Abstract base model that provides timestamps for created and updated as
    standard and also relies on UUID rather than sequential numbers as the
    primary key.
    """

    class Meta:
        abstract = True
