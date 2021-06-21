from django.db import models
from django.utils import timezone


class PackYearManager(models.Manager):
    def for_date(self, date):
        """Given a date, return the PackYear for that date."""
        return self.get(start_date__lte=date, end_date__gte=date)

    def current(self):
        """Return the current PackYear."""
        return self.for_date(date=timezone.now())

    def next(self):
        """Return the upcoming PackYear."""
        try:
            return self.current().get_next_by_end_date()
        except self.model.DoesNotExist:
            return None

    def previous(self):
        """Return the prior year's PackDate."""
        return self.current().get_previous_by_end_date()

    def recent(self):
        """
        Returns a queryset of the current year plus the year before and after.
        """
        return self.filter(
            start_date__lte=self.current().end_date + timezone.timedelta(days=1),
            end_date__gte=self.current().start_date - timezone.timedelta(days=1)
        )
