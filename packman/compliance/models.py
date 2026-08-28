from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import PackYear
from packman.core.models import TimeStampedUUIDModel

from .managers import EXPIRING_WINDOW, RequirementQuerySet, RequirementRecordQuerySet


class Requirement(TimeStampedUUIDModel):
    """
    A membership requirement the pack tracks each year, such as a Scouting
    America membership, a medical form, or pack dues.

    Requirements are configured by leadership rather than hard-coded, so a new
    one (Youth Protection Training, a background check) can be added without a
    code change.
    """

    class Audience(models.TextChoices):
        CUB = "CUB", _("Cubs")
        ADULT = "ADULT", _("Adults")
        FAMILY = "FAMILY", _("Families")

    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Shown to families so they know what is being asked of them and how to satisfy it."),
    )
    applies_to = models.CharField(
        _("applies to"),
        max_length=6,
        choices=Audience.choices,
        default=Audience.CUB,
        help_text=_("Who must satisfy this requirement? Family requirements are tracked once per family."),
    )
    tracks_expiration = models.BooleanField(
        _("expires"),
        default=True,
        help_text=_("Check this box if the requirement must be renewed, such as a medical form."),
    )
    default_duration_days = models.PositiveIntegerField(
        _("valid for"),
        blank=True,
        null=True,
        help_text=_("If set, an expiration date is suggested this many days after the completion date."),
    )
    include_contributors = models.BooleanField(
        _("include friends of the pack"),
        default=False,
        help_text=_(
            "Also track this requirement for adults who are Friends of the Pack "
            "rather than a parent or guardian of an active Cub."
        ),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Uncheck to stop tracking this requirement without deleting the records already collected."),
    )
    sort_order = models.IntegerField(_("sort order"), blank=True, null=True)

    objects = RequirementQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["slug", "applies_to", "is_active"])]
        ordering = ("sort_order", "name")
        verbose_name = _("Requirement")
        verbose_name_plural = _("Requirements")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("compliance:roster", kwargs={"slug": self.slug})

    def clean(self):
        if self.default_duration_days and not self.tracks_expiration:
            raise ValidationError(
                {"default_duration_days": _("A requirement that does not expire cannot have a duration.")},
                code="invalid",
            )

    @property
    def tracks_member(self):
        """True when this requirement is recorded against a person rather than a family."""
        return self.applies_to in (self.Audience.CUB, self.Audience.ADULT)


class RequirementRecord(TimeStampedUUIDModel):
    """
    One family's or member's standing against a single Requirement for a
    single pack year.

    The subject is either a member or a whole family. ``member`` points at
    ``membership.Member`` rather than Scout or Adult, because both inherit from
    it -- one foreign key covers both. ``family`` is set on every record,
    including member-scoped ones, so a family's page is a single indexed query.
    """

    class Status(models.TextChoices):
        NOT_STARTED = "NEW", _("Not started")
        COMPLETE = "OK", _("Complete")
        WAIVED = "NA", _("Waived")

    class Health(models.TextChoices):
        """
        The state a record is actually in, derived from its status and dates.

        The first three values intentionally match ``Status`` so templates can
        compare against a single vocabulary.
        """

        NOT_STARTED = "NEW", _("Not started")
        COMPLETE = "OK", _("Complete")
        WAIVED = "NA", _("Waived")
        EXPIRING = "SOON", _("Expiring soon")
        EXPIRED = "EXP", _("Expired")

    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="records",
        related_query_name="record",
    )
    year = models.ForeignKey(
        PackYear,
        on_delete=models.CASCADE,
        default=PackYear.get_current,
        related_name="requirement_records",
        related_query_name="requirement_record",
        verbose_name=_("pack year"),
    )
    member = models.ForeignKey(
        "membership.Member",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="requirement_records",
        related_query_name="requirement_record",
        help_text=_("Leave blank for requirements tracked once for the whole family."),
    )
    family = models.ForeignKey(
        "membership.Family",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="requirement_records",
        related_query_name="requirement_record",
    )
    status = models.CharField(
        _("status"),
        max_length=3,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    completed_on = models.DateField(_("completed"), blank=True, null=True)
    expires_on = models.DateField(_("expires"), blank=True, null=True)
    notes = models.TextField(
        _("notes"),
        blank=True,
        help_text=_("Do not record medical details here. Note only what is needed to track the paperwork."),
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="recorded_requirement_records",
        verbose_name=_("recorded by"),
    )

    objects = RequirementRecordQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["requirement", "year", "member"],
                condition=Q(member__isnull=False),
                name="unique_member_requirement_per_year",
            ),
            models.UniqueConstraint(
                fields=["requirement", "year", "family"],
                condition=Q(member__isnull=True),
                name="unique_family_requirement_per_year",
            ),
            models.CheckConstraint(
                condition=Q(member__isnull=False) | Q(family__isnull=False),
                name="requirement_record_has_a_subject",
            ),
        ]
        indexes = [
            models.Index(fields=["year", "requirement", "status"]),
            models.Index(fields=["family", "year"]),
            models.Index(fields=["expires_on"]),
        ]
        ordering = ("-year", "requirement__sort_order", "requirement__name")
        permissions = [
            ("manage_records", _("Can record and edit membership requirements for any family")),
            ("view_all_records", _("Can view membership requirement status for all families")),
        ]
        verbose_name = _("Requirement Record")
        verbose_name_plural = _("Requirement Records")

    def __str__(self):
        return f"{self.year}: {self.subject} - {self.requirement}"

    def get_absolute_url(self):
        return reverse("compliance:record_update", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Denormalize the family from the member so that every record, whether
        # member- or family-scoped, can be found with a single filter.
        if self.member_id and not self.family_id:
            self.family = self.family_for_member(self.member)
        super().save(*args, **kwargs)

    def clean(self):
        audience = self.requirement.applies_to if self.requirement_id else None

        if audience == Requirement.Audience.FAMILY:
            if self.member_id:
                raise ValidationError(
                    {
                        "member": _("%(requirement)s is tracked for the whole family.")
                        % {"requirement": self.requirement}
                    },
                    code="invalid",
                )
            if not self.family_id:
                raise ValidationError({"family": _("Select the family this record belongs to.")}, code="invalid")

        elif audience in (Requirement.Audience.CUB, Requirement.Audience.ADULT):
            if not self.member_id:
                raise ValidationError({"member": _("Select the member this record belongs to.")}, code="invalid")
            expected_cub = audience == Requirement.Audience.CUB
            if self.member_is_cub(self.member) is not expected_cub:
                raise ValidationError(
                    {
                        "member": _("%(requirement)s applies to %(audience)s.")
                        % {
                            "requirement": self.requirement,
                            "audience": self.requirement.get_applies_to_display().lower(),
                        }
                    },
                    code="invalid",
                )

        if self.expires_on and self.completed_on and self.expires_on < self.completed_on:
            raise ValidationError(
                {"expires_on": _("A requirement cannot expire before it was completed.")},
                code="invalid",
            )

    @staticmethod
    def member_is_cub(member):
        return hasattr(member, "scout")

    @staticmethod
    def family_for_member(member):
        """
        ``Member`` itself has no family; it is declared separately on Adult and
        on Scout, so we have to ask the subclass.
        """
        for attr in ("scout", "adult"):
            child = getattr(member, attr, None)
            if child is not None:
                return child.family
        return None

    @property
    def subject(self):
        """The member or family this record is about."""
        return self.member or self.family

    @property
    def effective_status(self):
        """
        The record's real state, derived rather than stored, so that a date
        passing never requires a data migration.
        """
        if self.status != self.Status.COMPLETE:
            return self.Health(self.status)
        if not self.expires_on:
            return self.Health.COMPLETE

        today = timezone.localdate()
        if self.expires_on < today:
            return self.Health.EXPIRED
        if self.expires_on <= today + timezone.timedelta(days=EXPIRING_WINDOW):
            return self.Health.EXPIRING
        return self.Health.COMPLETE

    @property
    def is_satisfied(self):
        """True when nothing more is needed of the family right now."""
        return self.effective_status in (self.Health.COMPLETE, self.Health.EXPIRING, self.Health.WAIVED)
