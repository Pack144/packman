import uuid
from django.contrib.auth.models import Group
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from pack_calendar.models import PackYear


class Committee(models.Model):
    """
    A well run pack relies on its members stepping up to provide support.
    Define a list of ongoing committees on which Adults can offer their
    services to assist with pack operations.
    """
    name = models.CharField(
        max_length=64,
    )
    description = models.TextField(
        null=True,
        blank=True,
    )
    members = models.ManyToManyField(
        'membership.Adult',
        through='Membership',
    )
    leadership = models.BooleanField(
        _("Pack Leadership"),
        default=False,
        help_text=_("e.g. Akela, Assistant Akela, Den Leader"),
    )
    is_staff = models.BooleanField(
        _("Staff"),
        default=False,
        help_text=_("Designates whether members can log into this admin site.")
    )
    slug = models.SlugField(
        unique=True,
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ['-leadership', 'name']
        verbose_name = _("Committee")
        verbose_name_plural = _("Committees")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse_lazy('committees:detail', args=[self.slug])


class Membership(models.Model):
    """
    Tracks members who have signed up for a committee, the year of their
    service, and their position on the committee.
    """
    CHAIR = 1
    MEMBER = 2
    APPRENTICE = 3
    DEN_LEADER = 4
    AKELA = 5
    ASSISTANT_AKELA = 6
    POSITION_CHOICES = [
        (CHAIR, _("Chair")),
        (MEMBER, _("Member")),
        (APPRENTICE, _("Apprentice")),
        (DEN_LEADER, _("Den Leader")),
        (AKELA, _("Akela")),
        (ASSISTANT_AKELA, _("Assistant Akela")),
    ]

    member = models.ForeignKey(
        'membership.Adult',
        on_delete=models.CASCADE,
        related_name='committees',
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
    )
    position = models.PositiveSmallIntegerField(
        choices=POSITION_CHOICES,
        default=MEMBER,
    )
    den = models.ForeignKey(
        'dens.Den',
        on_delete=models.CASCADE,
        related_name='leadership',
        blank=True,
        null=True,
        help_text=_(
            "If the member is a Den Leader, which Den # are they supporting?"
        ),
    )
    year_served = models.ForeignKey(
        PackYear,
        on_delete=models.CASCADE,
        default=PackYear.get_current_pack_year_year,
        related_name='committee_memberships',
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ['year_served', 'den', 'position', 'member']
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.member} {self.year_served}"

    def save(self, *args, **kwargs):
        group, created = Group.objects.get_or_create(name=self.committee.name)
        if group not in self.member.groups.all():
            self.member.groups.add(group)
        super(Membership, self).save(*args, **kwargs)
