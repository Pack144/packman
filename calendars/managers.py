from django.db import models
from django.utils import timezone


class PackYearQuerySet(models.QuerySet):
    def for_date(self, date):
        return self.filter(start_date__lte=date, end_date__gte=date)


class PackYearManager(models.Manager):
    def get_queryset(self):
        return PackYearQuerySet(self.model, using=self._db)

    def for_date(self, date):
        return self.get_queryset().for_date(date=date)

    def current(self):
        return self.for_date(date=timezone.now())
