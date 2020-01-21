import uuid
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from pack_calendar.models import PackYear


class Committee(models.Model):
    """
    A well run pack relies on its members stepping up to provide support. Define a list of ongoing committees on which
    AdultMembers can offer their services to assist with pack operations.
    """
    name = models.CharField(max_length=64)
    description = models.TextField(null=True, blank=True)
    members = models.ManyToManyField('membership.AdultMember', through='Membership', related_name='committees')
    leadership = models.BooleanField(_("Pack Leadership"), default=False, help_text=_(
        "e.g. Akela, Assistant Akela, Den Leader"))

    slug = models.SlugField(unique=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-leadership', 'name']
        verbose_name = _("Committee")
        verbose_name_plural = _("Committees")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse_lazy('committee_detail', args=[self.slug])


class Membership(models.Model):
    """
    Tracks members who have signed up for a committee, the year their service, and their position
    """
    CHAIR = 1
    MEMBER = 2
    APPRENTICE = 3
    AKELA = 5
    ASSISTANT_AKELA = 6
    POSITION_CHOICES = [
        (CHAIR, _("Chair")),
        (MEMBER, _("Member")),
        (APPRENTICE, _("Apprentice")),
        (AKELA, _("Akela")),
        (ASSISTANT_AKELA, _("Assistant Akela")),
    ]
    member = models.ForeignKey('membership.AdultMember', on_delete=models.CASCADE, related_name='committee_memberships')
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='committee_memberships')
    position = models.PositiveSmallIntegerField(choices=POSITION_CHOICES, default=MEMBER)
    year_served = models.ForeignKey(PackYear,
                                    on_delete=models.CASCADE,
                                    default=PackYear.get_current_pack_year,
                                    related_name='committee_memberships')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year_served} {self.get_position_display()}: {self.member}"

    class Meta:
        ordering = ['year_served', 'position', 'member']
        verbose_name = _("Member")
        verbose_name_plural = _("Members")
