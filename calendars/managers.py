from django.db import models
from django.utils import timezone


class PackYearManager(models.Manager):
    def for_date(self, date):
        """Given a date, return the PackYear for that date"""
        return self.get(start_date__lte=date, end_date__gte=date)

    def current(self):
        """Return the current PackYear"""
        return self.for_date(date=timezone.now())
