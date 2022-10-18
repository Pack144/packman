from django.core.cache import cache
from django.db import models
from django.utils import timezone


class PackYearManager(models.Manager):
    def for_date(self, date):
        """Given a date, return the PackYear for that date."""
        return self.get(start_date__lte=date, end_date__gte=date)

    def current(self):
        """Return the current PackYear."""
        current_year = cache.get("current_year")

        if current_year is None:
            current_year = self.for_date(date=timezone.now())
            cache.set("current_year", current_year)

        return current_year

    def next(self):
        """Return the upcoming PackYear."""
        try:
            return self.filter(start_date__gt=self.current().end_date).earliest()
        except self.model.DoesNotExist:
            return None

    def previous(self):
        """Return the prior PackYear."""
        try:
            return self.filter(end_date__lt=self.current().start_date).latest()
        except self.model.DoesNotExist:
            return None

    def recent(self):
        """
        Returns a queryset of the current year plus the year before and after.
        """
        return self.filter(
            start_date__lte=self.current().end_date + timezone.timedelta(days=1),
            end_date__gte=self.current().start_date - timezone.timedelta(days=1),
        )

    def get_by_natural_key(self, years):
        split_years = years.split("-")
        if len(split_years):
            return self.get(start_date__year=split_years[0], end_date__year=split_years[1])
        else:
            return self.get(end_date__year=years)

