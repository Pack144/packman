import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from pack_calendar.models import PackYear


class Rank(models.Model):
    """
    All of the Cub Scout ranks are defined. Packs can specify which ranks they
    support.
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

    rank = models.PositiveSmallIntegerField(
        choices=RANK_CHOICES,
        unique=True,
    )
    description = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    date_added = models.DateField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ['rank']
        verbose_name = _("Rank")
        verbose_name_plural = _("Ranks")

    def __str__(self):
        return self.get_rank_display()

    def category(self):
        if self.rank < Rank.BOBCAT:
            # We shouldn't see this
            return None
        elif self.rank <= Rank.BEAR:
            # Bobcat - Bear
            return _("Animal")
        elif self.rank >= Rank.JR_WEBE:
            # Jr. & Sr. Webelos
            return _("Webelos")
        else:
            return None

    @property
    def patch(self):
        if self.rank == Rank.BOBCAT:
            return f"{settings.STATIC_URL}img/bobcat.png"
        elif self.rank == Rank.TIGER:
            return f"{settings.STATIC_URL}img/tiger.png"
        elif self.rank == Rank.WOLF:
            return f"{settings.STATIC_URL}img/wolf.png"
        elif self.rank == Rank.BEAR:
            return f"{settings.STATIC_URL}img/bear.png"
        elif Rank.JR_WEBE <= self.rank <= Rank.WEBE:
            return f"{settings.STATIC_URL}img/webelos.png"
        elif self.rank == Rank.ARROW:
            return f"{settings.STATIC_URL}img/arrowoflight.png"


class Den(models.Model):
    """ Each active cub should be a member of 1 den each Pack Year """

    number = models.PositiveSmallIntegerField(
        primary_key=True,
        help_text=_("The Den number"),
    )
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        related_name='dens',
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
        ordering = ['number']
        verbose_name = _("Den")
        verbose_name_plural = _("Dens")

    def __str__(self):
        return f"Den {self.number}"

    def get_absolute_url(self):
        return reverse('dens:detail', args=[int(self.number)])

    def active_cubs(self):
        return self.scouts.filter(
            year_assigned=PackYear.get_current_pack_year()
        )

    def count_current_members(self):
        return self.active_cubs().count()

    def get_rank_category(self):
        if self.rank:
            if self.rank.rank <= Rank.BEAR:
                return _("Animals")
            if self.rank.rank >= Rank.JR_WEBE:
                return _("Webelos")

    @property
    def patch(self):
        if self.number <= 10:
            return f"{settings.STATIC_URL}img/den_{self.number}_patch.jpg"

    @property
    def animals(self):
        return self.rank.rank <= Rank.BEAR

    @property
    def webelos(self):
        return self.rank.rank >= Rank.JR_WEBE

    count_current_members.short_description = _("# of Cubs")
    get_rank_category.admin_order_field = 'rank'
    get_rank_category.short_description = _("Rank Category")


class Membership(models.Model):
    """
    Tracks the year(s) a cub is assigned to a Den
    """
    scout = models.ForeignKey(
        'membership.Scout',
        on_delete=models.CASCADE,
        related_name='den',
    )
    den = models.ForeignKey(
        Den,
        on_delete=models.CASCADE,
        related_name='scouts',
    )
    year_assigned = models.ForeignKey(
        PackYear,
        on_delete=models.CASCADE,
        default=PackYear.get_current_pack_year_year,
        related_name='den_memberships',
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
        ordering = ['year_assigned', 'den', 'scout']
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.year_assigned}: {self.scout}"
