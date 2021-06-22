from django.contrib.auth.models import Group, Permission
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import PackYear
from packman.core.models import TimeStampedUUIDModel

from .managers import CommitteeQuerySet


class Committee(TimeStampedUUIDModel):
    """
    A well run pack relies on its members stepping up to provide support.
    Define a list of ongoing committees on which Adults can offer their
    services to assist with pack operations.
    """

    name = models.CharField(
        max_length=64,
    )
    description = models.TextField(
        blank=True,
        default="",
    )
    members = models.ManyToManyField(
        "membership.Adult",
        through="CommitteeMember",
    )
    leadership = models.BooleanField(
        _("Pack Leadership"),
        default=False,
        help_text=_("e.g. Akela, Assistant Akela, Den Leader"),
    )
    are_staff = models.BooleanField(
        _("Staff"),
        default=False,
        help_text=_("Designates whether members can log into this admin site."),
    )
    are_superusers = models.BooleanField(
        _("superusers"),
        default=False,
        help_text=_(
            'Designates that members of this committee have all permissions without '
            'explicitly assigning them.')
    )
    permissions = models.ManyToManyField(Permission, verbose_name=_("permissions"), blank=True)
    slug = models.SlugField(
        unique=True,
    )

    objects = CommitteeQuerySet.as_manager()

    class Meta:
        ordering = ["-leadership", "name"]
        verbose_name = _("Committee")
        verbose_name_plural = _("Committees")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse_lazy("committees:detail", args=[self.slug])


class CommitteeMember(TimeStampedUUIDModel):
    """
    Tracks members who have signed up for a committee, the year of their
    service, and their position on the committee.
    """

    class Position(models.IntegerChoices):
        CHAIR = 1, _("Chair")
        MEMBER = 2, _("Member")
        APPRENTICE = 3, _("Apprentice")
        DEN_LEADER = 4, _("Den Leader")
        AKELA = 5, _("Akela")
        ASSISTANT_AKELA = 6, _("Assistant Akela")

    year = models.ForeignKey(
        PackYear,
        on_delete=models.CASCADE,
        default=PackYear.get_current_pack_year_year,
        related_name="committee_memberships",
        related_query_name="committee_membership",
        verbose_name=_("year served")
    )
    position = models.IntegerField(
        choices=Position.choices,
        default=Position.MEMBER,
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        related_name="committee_members",
        related_query_name="committee_member",
    )
    member = models.ForeignKey(
        "membership.Adult",
        on_delete=models.CASCADE,
        related_name="committee_memberships",
        related_query_name="committee_membership",
    )
    den = models.ForeignKey(
        "dens.Den",
        on_delete=models.CASCADE,
        related_name="leadership",
        blank=True,
        null=True,
        help_text=_("If the member is a Den Leader, which Den # are they supporting?"),
    )

    class Meta:
        ordering = ["year", "den", "position", "member"]
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.member} {self.year}"
