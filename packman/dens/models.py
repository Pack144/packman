from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import PackYear
from packman.core.models import TimeStampedModel, TimeStampedUUIDModel


class Rank(TimeStampedUUIDModel):
    """
    All the Cub Scout ranks are defined by BSA. Packs can specify which ranks
    they support.
    """

    class RankChoices(models.IntegerChoices):
        LION = 1, _("Lion")
        TIGER = 2, _("Tiger")
        WOLF = 3, _("Wolf")
        BEAR = 4, _("Bear")
        JR_WEBE = 5, _("Jr. Webelo")
        SR_WEBE = 6, _("Sr. Webelo")
        WEBE = 7, _("Webelo")
        ARROW = 8, _("Arrow of Light")

    rank = models.IntegerField(
        choices=RankChoices.choices,
        unique=True,
    )
    description = models.CharField(
        max_length=128,
        blank=True,
    )

    class Meta:
        ordering = ["rank"]
        verbose_name = _("Rank")
        verbose_name_plural = _("Ranks")

    def __str__(self):
        return self.get_rank_display()

    def category(self):
        if self.rank < Rank.RankChoices.LION:
            # We shouldn't see this
            return None
        elif self.rank <= Rank.RankChoices.BEAR:
            # Lion - Bear
            return _("Animal")
        elif self.rank >= Rank.RankChoices.JR_WEBE:
            # Jr. & Sr. Webelos
            return _("Webelos")
        else:
            return None

    @property
    def patch(self):
        if self.rank == Rank.RankChoices.LION:
            return f"{settings.STATIC_URL}img/lion.png"
        elif self.rank == Rank.RankChoices.TIGER:
            return f"{settings.STATIC_URL}img/tiger.png"
        elif self.rank == Rank.RankChoices.WOLF:
            return f"{settings.STATIC_URL}img/wolf.png"
        elif self.rank == Rank.RankChoices.BEAR:
            return f"{settings.STATIC_URL}img/bear.png"
        elif Rank.RankChoices.JR_WEBE <= self.rank <= Rank.RankChoices.WEBE:
            return f"{settings.STATIC_URL}img/webelos.png"
        elif self.rank == Rank.RankChoices.ARROW:
            return f"{settings.STATIC_URL}img/arrowoflight.png"


class Den(TimeStampedModel):
    """Each active cub should be a member of 1 den each Pack Year"""

    number = models.IntegerField(
        primary_key=True,
        help_text=_("The Den number"),
    )
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        related_name="dens",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["number"]
        verbose_name = _("Den")
        verbose_name_plural = _("Dens")

    def __str__(self):
        return f"Den {self.number}"

    def get_absolute_url(self):
        return reverse("dens:detail", args=[int(self.number)])

    def active_cubs(self):
        return self.scouts.filter(year_assigned=PackYear.get_current_pack_year())

    def count_current_members(self):
        return self.active_cubs().count()

    def get_rank_category(self):
        if self.rank:
            if self.rank.rank <= Rank.RankChoices.BEAR:
                return _("Animals")
            if self.rank.rank >= Rank.RankChoices.JR_WEBE:
                return _("Webelos")

    @property
    def patch(self):
        if self.number <= 10:
            return f"{settings.STATIC_URL}img/den_{self.number}_patch.jpg"

    @property
    def animals(self):
        return self.rank.rank <= Rank.RankChoices.BEAR

    @property
    def webelos(self):
        return self.rank.rank >= Rank.RankChoices.JR_WEBE

    count_current_members.short_description = _("# of Cubs")
    get_rank_category.admin_order_field = "rank"
    get_rank_category.short_description = _("Rank Category")


class Membership(TimeStampedUUIDModel):
    """
    Tracks the year(s) a cub is assigned to a Den
    """

    scout = models.ForeignKey(
        "membership.Scout",
        on_delete=models.CASCADE,
        related_name="den_memberships",
    )
    den = models.ForeignKey(
        Den,
        on_delete=models.CASCADE,
        related_name="scouts",
    )
    year_assigned = models.ForeignKey(
        PackYear,
        on_delete=models.CASCADE,
        default=PackYear.get_current_pack_year_year,
        related_name="den_memberships",
    )

    class Meta:
        ordering = ["year_assigned", "den", "scout"]
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.year_assigned}: {self.scout}"
