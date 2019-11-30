import uuid
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .managers import AccountManager


def member_headshot_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/headshots/user_slug/<filename>
    return 'headshots/{0}/{1}'.format(slugify(instance.full_name()), filename)


def couple_of_years_ago():
    # give a year 2-3 years in the past as a starting point for the Scout year_started_kindergarten field
    return timezone.now().year - 2


class Account(AbstractBaseUser, PermissionsMixin):
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
        return self.email

    def email_user(self, subject, message, from_email=None, **kwargs):
        """ Sends an email to this User """
        send_mail(subject, message, from_email, [self.email], **kwargs)


class Member(models.Model):
    """
    The member profile used to store additional information about this person
    """
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Prefer not to say'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, blank=True, null=True)
    last_name = models.CharField(max_length=32)
    nickname = models.CharField(max_length=32, blank=True, null=True, help_text=_(
        "If there is another name you prefer to be called, tell us what it is we will use that on the website."))
    photo = models.ImageField(upload_to=member_headshot_path, blank=True, null=True, help_text=_(
        "We use member photos on the website to help match names with faces."))
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)

    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = _('All Members')

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        if hasattr(self, 'parent'):
            return reverse('parent_detail', args=[str(self.id)])
        elif hasattr(self, 'scout'):
            return reverse('scout_detail', args=[str(self.id)])
        else:
            return None

    @property
    def full_name(self):
        """ Return the member's first and last name, replacing first name with a nickname if one has been given """
        return "{} {}".format(self.name, self.last_name)

    @property
    def name(self):
        """ Return the member's nickname, if given, or first name if nickname isn't specified """
        if self.nickname:
            return self.nickname
        else:
            return self.first_name

    def thumbnail(self):
        """ Reduce the size of the member's avatar to fit in the detail card """
        pass


class Parent(Member):
    """
    Any adult member such as a parent, guardian, or other use this model
    """
    ROLE_CHOICES = (
        ('P', 'Parent/Guardian'),
        ('C', 'Contributor'),
    )
    role = models.CharField(max_length=1, choices=ROLE_CHOICES, default='P')
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile', verbose_name='email')

    @property
    def email(self):
        return self.account.email

    def get_active_scouts(self):
        """ Return a list of all currently active scouts associated with this member. """
        return self.children.filter(status__exact='A')

    @property
    def is_active(self):
        """ If member has active scouts, then they should also be considered active in the pack. """
        if self.get_active_scouts():
            return True
        else:
            return False


class Scout(Member):
    """
    Cub scouts use this model to store profile details
    """
    STATUS_CHOICES = (
        ('W', 'Applied'),
        ('P', 'Approved'),
        ('A', 'Active'),
        ('I', 'Inactive'),
        ('D', 'Denied'),
        ('G', 'Graduated'),
    )

    birthday = models.DateField(blank=True, null=True)
    school = models.ForeignKey('address_book.Venue', on_delete=models.CASCADE, blank=True, null=True,
                               limit_choices_to={'type__type__icontains': 'School'}, help_text=_(
            "Tell us what school your child attends. If your school isn't listed, tell us in the comments section."))
    year_started_kindergarten = models.PositiveSmallIntegerField(default=couple_of_years_ago, help_text=_(
        "What year did your child start kindergarten? We use this to assign your child to an appropriate den."))
    referral = models.CharField(max_length=128, blank=True, null=True, help_text=_(
        "If you know someone who is already in the pack, you can tell us their name."))
    comments = models.TextField(blank=True, null=True, help_text=_(
        "What other information should we consider when reviewing your application?"))

    parents = models.ManyToManyField(Parent, related_name='children', through='Relationship', blank=True)

    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='I')
    start_date = models.DateField(blank=True, null=True)

    @property
    def age(self):
        """ Calculates the cub scout's age when a birthday is specified """
        if not self.birthday:
            return None
        today = timezone.now()
        return today.year - self.birthday.year - (
                (today.month, today.day) < (self.birthday.month, self.birthday.day))

    def get_siblings(self):
        """ Return a list of other Scouts who share the same parent(s) """
        return Scout.objects.filter(~Q(id=self.id), Q(parents__in=self.parents.all())).distinct()

    @property
    def grade(self):
        """ Based on when this cub started school, what grade should they be in now? """
        this_year = timezone.now().year
        if timezone.now().month < 9:  # assuming that a school year begins in September
            this_year -= 1
        calculated_grade = this_year - self.year_started_kindergarten

        if calculated_grade == 0:
            # this Scout is a kindergartner
            return 'K'
        elif calculated_grade < 0:
            # this Scout hasn't started Kindergarten yet
            return None
        elif calculated_grade <= 12:
            return calculated_grade
        else:
            # this Scout isn't in grade school anymore
            return None


class Relationship(models.Model):
    """ Track the relationship a member has with a scout """
    RELATIONSHIP_CHOICES = (
        ('M', 'Mom'),
        ('F', 'Dad'),
        ('GM', 'Grandmother'),
        ('GF', 'Grandfather'),
        ('A', 'Aunt'),
        ('U', 'Uncle'),
        ('G', 'Guardian'),
        ('FF', 'Friend of the Family'),
        ('O', 'Other/Undefined')
    )
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    child = models.ForeignKey(Scout, on_delete=models.CASCADE)
    relationship_to_child = models.CharField(max_length=2, choices=RELATIONSHIP_CHOICES, default='O')

    def __str__(self):
        return "{}'s {}, {}".format(self.child.full_name, self.get_relationship_to_child_display(), self.parent.full_name)
