from django.db import models
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import Event
from packman.committees.models import Committee
from packman.core.models import TimeStampedUUIDModel
from packman.membership.models import Member


class Attendance(TimeStampedUUIDModel):
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
    )
    members = models.ManyToManyField(Member)
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="attendance",
    )

    class Meta:
        # indexes = [models.Index(fields=["name"])]
        ordering = ["event"]
        verbose_name = _("Attendance")
        verbose_name_plural = _("Attendance")

    def __str__(self):
        if self.event:
            return f"{self.event.start} {self.event.name}"

    # Attendance.objects.exclude(event__in=Event.objects.all())
