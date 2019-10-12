import uuid
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import assign_perm

from .managers import AccountManager


def avatar_upload_location(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.id, filename)


class Account(AbstractBaseUser, PermissionsMixin, GuardianUserMixin):
    """
    An e-mail based user account, used to log into the website
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = AccountManager()

    def __str__(self):
        if self.profile.full_name != '':
            return '{} ({})'.format(self.email, self.profile.full_name())
        else:
            return self.email

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)


class Member(models.Model):
    """
    The member profile used to store additional information about the member
    """
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Prefer not to say'),
    )
    STATUS_CHOICES = (
        ('W', 'Wait Listed'),
        ('A', 'Active'),
        ('I', 'Inactive'),
        ('G', 'Graduated'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    last_name = models.CharField(max_length=32)
    nickname = models.CharField(max_length=32, null=True, blank=True,
                                help_text=_('If there is another name you prefer go by, tell us what it is we will use '
                                            'that on the website.'))
    avatar = models.ImageField(upload_to=avatar_upload_location, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='I')

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = _('all members')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.full_name()

    def get_absolute_url(self):
        if hasattr(self, 'parent'):
            return reverse('parent_detail', args=[str(self.id)])
        elif hasattr(self, 'scout'):
            return reverse('scout_detail', args=[str(self.id)])
        else:
            return None

    def full_name(self):
        """ Return the member's first and last name, replacing first name with a nickname if one has been given """
        return "{} {}".format(self.short_name(), self.last_name)

    def short_name(self):
        """ Return the member's nickname, if given, or first name if nickname isn't specified """
        if self.nickname:
            return self.nickname
        else:
            return self.first_name


class Scout(Member):
    """
    Cub scouts use this model to store profile details
    """
    birthday = models.DateField(null=True, blank=True)

    def age(self):
        """ Calculates the cub scout's age when a birthday is specified """
        if not self.birthday:
            return None
        today = timezone.now()
        return today.year - self.birthday.year - (
                (today.month, today.day) < (self.birthday.month, self.birthday.day))

    def get_parents(self):
        return self.parents.all()

    def get_siblings(self):
        siblings = []
        for parent in self.parents.all():
            siblings += Scout.objects.filter(
                ~Q(id=self.id),
                Q(parents=parent)
            )
        return siblings


class Parent(Member):
    """
    Any adult member such as a parent, guardian, or other use this model
    """
    ROLE_CHOICES = (
        ('P', 'Parent/Guardian'),
        ('C', 'Contributor'),
    )
    children = models.ManyToManyField(Scout, related_name='parents', blank=True)
    role = models.CharField(max_length=1, choices=ROLE_CHOICES, default='P')
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile', verbose_name='email')

    def email(self):
        return self.account.email

    def get_published_phone_numbers(self):
        return self.phone_numbers.filter('is_published')
