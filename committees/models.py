from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Committee(models.Model):
    """
    A well run pack relies on its members stepping up to provide support. Define a list of ongoing committees on which
    AdultMembers can offer their services to assist with pack operations.
    """
    name = models.CharField(max_length=64)
    description = models.TextField(null=True, blank=True)
    leadership = models.ManyToManyField('membership.AdultMember', through='Membership', related_name='committees')

    slug = models.SlugField(unique=True)
    date_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
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
    POSITION_CHOICES = [
        (CHAIR, _("Chair")),
        (MEMBER, _("Member")),
        (APPRENTICE, _("Apprentice")),
    ]
    member = models.ForeignKey('membership.AdultMember', on_delete=models.CASCADE)
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField(choices=POSITION_CHOICES, default=MEMBER)
    year_served = models.PositiveSmallIntegerField(default=timezone.now().year)

    date_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year_served} {self.get_position_display()}: {self.member}"

    class Meta:
        ordering = ['year_served', 'position', 'member']
        verbose_name = _("Member")
        verbose_name_plural = _("Members")
