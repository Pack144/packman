from django.contrib.auth.models import UserManager
from django.db import models

from dens.models import Rank
from pack_calendar.models import PackYear


class MemberManager(UserManager):

    def _create_user(self, email, password, **extra_fields):
        """
        Custom user model manager where email is the unique identifiers for authentication instead of usernames.
        All other code is shamelessly ripped off directly from Django's own UserManager
        https://github.com/django/django/blob/master/django/contrib/auth/models.py
        """
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class CurrentTigersManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank=Rank.TIGER)


class CurrentWolvesManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank=Rank.WOLF)


class CurrentBearsManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank=Rank.BEAR)


class CurrentJrWebesManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank=Rank.JR_WEBE)


class CurrentSrWebesManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank=Rank.SR_WEBE)


class CurrentAnimalsManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank__lte=Rank.BEAR)


class CurrentWebelosManager(models.Manager):
    def get_query_set(self):
        return self.objects.filter(den__year_assigned=PackYear.get_current_pack_year()).filter(
            den__den__rank__rank__gte=Rank.JR_WEBE)
