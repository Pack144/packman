from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import AccountManager


class Account(AbstractBaseUser, PermissionsMixin):
    """
    An e-mail based user account, used to log into the website
    """
    email = models.EmailField(_('email address'), unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = AccountManager()

    def __str__(self):
        if self.profile.full_name:
            return self.profile.full_name()
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

    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    last_name = models.CharField(max_length=32)
    nickname = models.CharField(max_length=32, null=True, blank=True,
                                help_text=_('If there is another name you go by, putting it here will override what '
                                            'gets displayed on the website.'))
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
        return reverse('member_detail', args=[str(self.id)])

    def full_name(self):
        """ Return the member's first and last name, replacing first name with a nickname if one has been given """
        return "{} {}".format(self.short_name(), self.last_name)

    def short_name(self):
        """ Return the member's nickname, if given, or first name if nickname isn't specified """
        if self.nickname:
            return self.nickname
        else:
            return self.first_name


class Family(models.Model):
    custom_name = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        verbose_name_plural = _('Families')

    def __str__(self):
        return self.family_name()

    def family_name(self):
        # TODO: come up with a better way to name a family
        if self.custom_name:
            return self.custom_name
        elif Count(self.children):
            return 'children'
        elif Count(self.parents):
            return 'parents'
        else:
            return 'neither'


class Scout(Member):
    """
    Cub scouts use this model to store profile details
    """
    birthday = models.DateField(null=True, blank=True)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='children', null=True)

    def age(self):
        """ Calculates the cub scout's age when a birthday is specified """
        if not self.birthday:
            return None
        today = timezone.now()
        return today.year - self.birthday.year - (
                (today.month, today.day) < (self.birthday.month, self.birthday.day))


class Parent(Member):
    """
    Any adult member such as a parent, guardian, or other use this model
    """
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile', null=True)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='parents', null=True)

    def email(self):
        return self.account.email
