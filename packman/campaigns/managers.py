from django.db import models
from django.utils import timezone


class CampaignQuerySet(models.QuerySet):
    def current(self):
        return self.filter(ordering_opens__lte=timezone.now(), ordering_closes__gte=timezone.now())


class CampaignManager(models.Manager):
    def get_queryset(self):
        return CampaignQuerySet(self.model, using=self._db)

    def current(self):
        return self.get_queryset().current()
