import uuid
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from membership.models import ChildMember


class Rank(models.Model):
    """
    All of the Cub Scout ranks are defined. Packs can specify which ranks they support.
    """
    BOBCAT = 1
    TIGER = 2
    WOLF = 3
    BEAR = 4
    JR_WEBE = 5
    SR_WEBE = 6
    WEBE = 7
    ARROW = 8
    RANK_CHOICES = (
        (BOBCAT, _("Bobcat")),
        (TIGER, _("Tiger")),
        (WOLF, _("Wolf")),
        (BEAR, _("Bear")),
        (JR_WEBE, _("Jr. Webelo")),
        (SR_WEBE, _("Sr. Webelo")),
        (WEBE, _("Webelo")),
        (ARROW, _("Arrow of Light")),
    )
    rank = models.PositiveSmallIntegerField(choices=RANK_CHOICES, unique=True)
    description = models.CharField(max_length=128, blank=True, null=True)
    patch = models.ImageField(upload_to='dens/rank', blank=True, null=True,)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_added = models.DateField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_rank_display()

    class Meta:
        ordering = ['rank']
        verbose_name = _("Rank")
        verbose_name_plural = _("Ranks")

    @property
    def category(self):
        if self.rank < Rank.BOBCAT:
            # We shouldn't see this
            return None
        elif self.rank <= Rank.BEAR:
            # Bobcat - Bear
            return _("Animal")
        elif self.rank >= Rank.JR_WEBE:
            # Jr. & Sr. Webelos
            return _('Webelos')
        else:
            return None


class Den(models.Model):
    """ Each cub should be a member of 1 den """

    number = models.PositiveSmallIntegerField(primary_key=True, help_text=_("The Den's Number"))
    rank = models.ForeignKey(Rank, on_delete=models.CASCADE, related_name='dens', blank=True, null=True)
    patch = models.ImageField(upload_to='dens', blank=True, null=True, help_text=_(
        "Display an image of the den's patch on the den detail page and member detail pages."))

    date_added = models.DateField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        verbose_name = _("Den")
        verbose_name_plural = _("Dens")

    def __str__(self):
        return f"Den {self.number}"

    def get_absolute_url(self):
        return reverse('den_detail', args=[int(self.number)])

    def active_cubs(self):
        return self.scouts.filter(status__exact=ChildMember.ACTIVE)
