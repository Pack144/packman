import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.signal_handlers import generate_aliases
from easy_thumbnails.signals import saved_file

from dens.models import Den
from pack_calendar.models import PackYear
from .managers import MemberManager, ScoutManager


def get_photo_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/headshots/user_slug/<filename>
    return f"headshots/{instance.slug}/{filename}"


def get_two_years_ago():
    """
    Calculate the year two years before the current year.
    Used by the Scout model to provide a default for when they start school.
    """
    return timezone.now().year - 2


class Member(models.Model):
    """
    A class implementing the details we would want to capture for any person.
    Used by the later models, Adult and Scout, to populate common fields used.
    """

    # Define static options for gender
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'
    GENDER_CHOICES = (
        (MALE, _("Male")),
        (FEMALE, _("Female")),
        (OTHER, _("Prefer not to say"))
    )

    # Personal information
    prefix = models.CharField(
        _("Title"),
        max_length=16,
        blank=True,
        null=True
    )
    first_name = models.CharField(
        _("First Name"),
        max_length=30
    )
    middle_name = models.CharField(
        _("Middle Name"),
        max_length=32,
        blank=True,
        null=True
    )
    last_name = models.CharField(
        _("Last Name"),
        max_length=150
    )
    suffix = models.CharField(
        _("Suffix"),
        max_length=8,
        blank=True,
        null=True
    )
    nickname = models.CharField(
        _("Nickname"),
        max_length=32,
        blank=True,
        null=True,
        help_text=_(
            "If there is another name you prefer to be called, tell us and we "
            "will use it any time we refer to you on the website.")
    )
    gender = models.CharField(
        _("Gender"),
        max_length=1,
        choices=GENDER_CHOICES,
        default=None,
        blank=False,
        null=True
    )
    photo = ThumbnailerImageField(
        _("Headshot Photo"),
        upload_to=get_photo_path,
        blank=True,
        null=True,
        help_text=_(
            "We use member photos on the website to help match names with "
            "faces.")
    )
    date_of_birth = models.DateField(
        _("Birthday"),
        blank=True,
        null=True
    )

    # Administrative
    slug = models.SlugField(
        unique=True,
        blank=True,
        null=True
    )
    pack_comments = models.TextField(
        _("Pack Comments"),
        blank=True,
        null=True,
        help_text=_(
            "Used by pack leadership to keep notes about a specific member. "
            "This information is not generally disclosed to the member unless "
            "they are granted access to Membership.")
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [models.Index(fields=[
            'first_name',
            'middle_name',
            'nickname',
            'last_name',
            'gender'
        ])]
        ordering = ['last_name', 'nickname', 'first_name']

    def __str__(self):
        return self.get_full_name()

    def save(self, *args, **kwargs):
        if not self.slug:
            candidates = [self.get_full_name()]
            if self.middle_name and self.suffix:
                candidates.append(
                    f"{self.first_name} "
                    f"{self.middle_name[0]} "
                    f"{self.last_name} "
                    f"{self.suffix}"
                )
                candidates.append(
                    f"{self.first_name} "
                    f"{self.middle_name} "
                    f"{self.last_name} "
                    f"{self.suffix}"
                )
            elif self.suffix:
                candidates.append(
                    f"{self.first_name} "
                    f"{self.last_name} "
                    f"{self.suffix}"
                )
            elif self.middle_name:
                candidates.append(
                    f"{self.first_name} "
                    f"{self.middle_name[0]} "
                    f"{self.last_name}"
                )
                candidates.append(
                    f"{self.first_name} "
                    f"{self.middle_name} "
                    f"{self.last_name}"
                )
            self.choose_slug(candidates=candidates)
            if not self.slug:
                # None of the normal candidates seem to have worked or we would
                # have a slug now. Start adding digits to the end of their name
                candidates = [f"{self.get_full_name()} {i}" for i in
                              range(1, 100)]
                self.choose_slug(candidates=candidates)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        if hasattr(self, 'adult'):
            return reverse('parent_detail', kwargs={'slug': self.slug})
        elif hasattr(self, 'scout'):
            return reverse('scout_detail', kwargs={'slug': self.slug})
        else:
            return None

    def get_full_name(self):
        """
        Return the short name, either first_name or nickname, plus the
        last_name, with a space in between.
        """
        if self.suffix:
            return f"{self.get_short_name()} {self.last_name} {self.suffix}"
        else:
            return f"{self.get_short_name()} {self.last_name}"

    def get_short_name(self):
        """ Return either the first_name or nickname for the member. """
        return self.nickname if self.nickname else self.first_name

    def choose_slug(self, candidates):
        for candidate in candidates:
            if not Member.objects.filter(slug=slugify(candidate)):
                self.slug = slugify(candidate)
                break
        return self.slug

    @property
    def age(self):
        """ If we have a birthday, calculate the current age of the member. """
        if self.date_of_birth:
            today = timezone.now()
            return today.year - self.date_of_birth.year - (
                # This will calculate a 1 if the date hasn't come yet this year
                    (today.month, today.day) <
                    (self.date_of_birth.month, self.date_of_birth.day)
            )


class Family(models.Model):
    """ Track the relationship between members """
    name = models.CharField(
        max_length=64,
        blank=True,
        null=True,
    )

    pack_comments = models.TextField(
        _("Pack Comments"),
        blank=True,
        null=True,
        help_text=_(
            "Used by pack leadership to keep notes about a specific family. "
            "This information is not generally disclosed to members unless "
            "they are granted access to Membership."),
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    legacy_id = models.PositiveSmallIntegerField(
        unique=True,
        blank=True,
        null=True,
    )
    date_added = models.DateField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [models.Index(fields=['name'])]
        ordering = ['date_added']
        verbose_name = _("Family")
        verbose_name_plural = _("Families")

    def __str__(self):
        if self.name:
            return self.name

    def save(self, *args, **kwargs):
        last_names = []
        for parent in self.adults.all():
            if parent.last_name not in last_names:
                last_names.append(parent.last_name)
        self.name = "-".join(last_names) + " Family"
        return super().save(*args, **kwargs)


class Adult(AbstractBaseUser, PermissionsMixin, Member):
    """
    Any adult member such as a parent, guardian, or other use this model. Being
    an adult gives you access to the website with an e-mail address and
    password.
    """

    # Define the various roles an adult member can have within the Pack
    PARENT = 'P'
    GUARDIAN = 'G'
    CONTRIBUTOR = 'C'
    ROLE_CHOICES = (
        (PARENT, _("Parent")),
        (GUARDIAN, _("Guardian")),
        (CONTRIBUTOR, _("Friend of the Pack")),
    )

    email = models.EmailField(
        _('Email Address'),
        unique=True
    )
    is_published = models.BooleanField(
        _('Published'),
        default=True,
        help_text=_("Display this address to other members of the pack."),
    )

    role = models.CharField(
        _('Role'),
        max_length=1,
        choices=ROLE_CHOICES,
        default=PARENT,
    )
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name='adults',
        blank=True,
        null=True,
    )

    objects = MemberManager()
    _is_staff = models.BooleanField(
        _("Staff"),
        default=False,
        help_text=_(
            "Designates whether the user can log into this admin site."
        ),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        indexes = [models.Index(fields=['role', 'email', 'family'])]
        ordering = ['last_name', 'nickname', 'first_name']
        verbose_name = _("Adult")
        verbose_name_plural = _("Adults")

    def __str__(self):
        return self.get_full_name()

    def save(self, *args, **kwargs):
        super(Adult, self).save(*args, **kwargs)
        if self.family:
            self.family.save()

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def get_active_scouts(self):
        """
        Return a list of currently active scouts associated with this member.
        """
        if self.family:
            return self.family.children.filter(status__exact=Scout.ACTIVE)

    def get_partners(self):
        """ Return a list of other parents who share the same scout(s) """
        if self.family:
            return self.family.adults.exclude(uuid=self.uuid)

    @property
    def is_staff(self):
        if self._is_staff or self.committees.filter(
                committee__is_staff=True).filter(
            year_served=PackYear.get_current_pack_year()
        ):
            return True

    @property
    def active(self):
        """
        If member has scouts who are currently active, then they should also be
        considered to be active in the Pack.
        """
        if self.get_active_scouts():
            return True
        else:
            return False


class Scout(Member):
    """
    Cub scouts use this model to store profile details
    """

    # Define the various statuses a Scout can be. Are the a currently active
    # member, new applicant, or even graduated?
    APPLIED = 1
    DENIED = 2
    APPROVED = 3
    ACTIVE = 4
    INACTIVE = 5
    GRADUATED = 6
    STATUS_CHOICES = (
        (APPLIED, _("Applied")),
        (DENIED, _("Denied")),
        (APPROVED, _("Approved")),
        (ACTIVE, _("Active")),
        (INACTIVE, _("Inactive")),
        (GRADUATED, _("Graduated")),
    )

    school = models.ForeignKey(
        'address_book.Venue',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        limit_choices_to={'type__type__icontains': 'School'},
        help_text=_(
            "Tell us what school your child attends. If your school isn't "
            "listed, tell us in the comments section."),
    )

    # Give parents an opportunity to add more detail to their application
    reference = models.CharField(
        _("Referral(s)"),
        max_length=128,
        blank=True,
        null=True,
        help_text=_(
            "If you know someone who is already in the pack, you can tell us "
            "their name so we can credit them for referring you."),
    )
    member_comments = models.TextField(
        _("Comments"),
        blank=True,
        null=True,
        help_text=_(
            "What other information should we consider when reviewing your "
            "application?"),
    )

    # These fields should be managed by the person(s) in charge of membership
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name='children',
        blank=True,
        null=True,
    )
    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=STATUS_CHOICES,
        default=APPLIED,
        help_text=(
            "What is the Cub's current status? A new cub who has not been "
            "reviewed will start as 'Applied'. Membership can choose then to "
            "approve or decline the application, or make them active. Once a "
            "Cub is no longer active in the pack, either through graduation "
            "or attrition, note that change' here. Any adult member connected "
            "to this Cub will get access only once the Cub's status is "
            "'Active' or 'Approved'."),
    )
    dens = models.ManyToManyField(
        'dens.Den',
        blank=True,
        through='dens.Membership',
    )

    # Important dates
    started_school = models.PositiveSmallIntegerField(
        _("Kindergarten Year"),
        default=get_two_years_ago,
        null=True,
        help_text=_(
            "What year did your child start kindergarten? We use this to "
            "calculate their grade year in school and assign your child to an "
            "appropriate den."),
    )
    started_pack = models.DateField(
        _("Date Started"),
        blank=True,
        null=True,
        help_text=_(
            "When does this cub join their first activity with the pack?"),
    )

    # Custom managers to simplify the selection of cubs based on their rank
    # All animal ranks from Tiger through Bear
    objects = ScoutManager()

    class Meta:
        indexes = [models.Index(
            fields=['school', 'family', 'status', 'started_school']
        )]
        verbose_name = _("Cub")
        verbose_name_plural = _("Cubs")

    def get_siblings(self):
        """ Return a list of other Scouts who share the same parent(s) """
        if self.family:
            return self.family.children.exclude(uuid=self.uuid)

    @property
    def current_den(self):
        return Den.objects.get(
            scouts__scout=self,
            scouts__year_assigned=PackYear.get_current_pack_year()
        )

    @property
    def grade(self):
        """
        Based on when this cub started school, what grade should they be in
        now?
        """
        if self.started_school:
            this_year = timezone.now().year
            if timezone.now().month < 9:  # assume school year begins September
                this_year -= 1

            calculated_grade = this_year - self.started_school
            if calculated_grade < 0:
                # this Scout hasn't started Kindergarten yet
                return None
            elif calculated_grade == 0:
                # this Scout is a kindergartner
                return 'K'
            elif calculated_grade <= 12:
                return calculated_grade
            else:
                # this Scout isn't in grade school anymore
                return None

    def get_grade(self):
        return self.grade

    @property
    def rank(self):
        """ A cub's rank is derived from the den they are a member of. """
        return self.den.rank

    get_grade.admin_order_field = 'started_school'
    get_grade.short_description = _("School Grade")


saved_file.connect(generate_aliases)
