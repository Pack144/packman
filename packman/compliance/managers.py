from django.db import models
from django.db.models import Q
from django.utils import timezone

from packman.calendars.models import PackYear

#: Number of days before an expiration date that a record is considered "expiring soon".
EXPIRING_WINDOW = 60


class RequirementQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_audience(self, audience):
        return self.filter(applies_to=audience)


class RequirementRecordQuerySet(models.QuerySet):
    def for_year(self, year=None):
        return self.filter(year=year or PackYear.objects.current())

    def for_family(self, family):
        return self.filter(family=family)

    def cubs(self):
        return self.filter(requirement__applies_to=self.model.requirement.field.related_model.Audience.CUB)

    def adults(self):
        return self.filter(requirement__applies_to=self.model.requirement.field.related_model.Audience.ADULT)

    def families(self):
        return self.filter(requirement__applies_to=self.model.requirement.field.related_model.Audience.FAMILY)

    def complete(self):
        """Recorded complete and not past its expiration date."""
        return self.filter(
            Q(status=self.model.Status.COMPLETE)
            & (Q(expires_on__isnull=True) | Q(expires_on__gte=timezone.localdate()))
        )

    def outstanding(self):
        """Nothing recorded yet. Waived records are deliberately excluded."""
        return self.filter(status=self.model.Status.NOT_STARTED)

    def waived(self):
        return self.filter(status=self.model.Status.WAIVED)

    def expired(self):
        return self.filter(status=self.model.Status.COMPLETE, expires_on__lt=timezone.localdate())

    def expiring(self, within_days=EXPIRING_WINDOW):
        """Complete, but expiring within the given window."""
        today = timezone.localdate()
        return self.filter(
            status=self.model.Status.COMPLETE,
            expires_on__gte=today,
            expires_on__lte=today + timezone.timedelta(days=within_days),
        )

    def needs_attention(self, within_days=EXPIRING_WINDOW):
        """Everything leadership needs to chase: outstanding, expired, or expiring soon."""
        today = timezone.localdate()
        return self.filter(
            Q(status=self.model.Status.NOT_STARTED)
            | Q(
                status=self.model.Status.COMPLETE,
                expires_on__lte=today + timezone.timedelta(days=within_days),
            )
        )
