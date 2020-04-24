from django.db import models

from pack_calendar.models import PackYear

from .models import Rank


class AnimalsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(rank__lte=Rank.BEAR)


class WebelosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(rank__gte=Rank.JR_WEBE)


class TigerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(rank__exact=Rank.TIGER)


class WolfManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(rank__exact=Rank.WOLF)


class BearManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(rank__exact=Rank.BEAR)