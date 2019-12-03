from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Rank(models.Model):
    BOBCAT = 1
    TIGER = 2
    WOLF = 3
    BEAR = 4
    JR_WEBE = 5
    SR_WEBE = 6
    ARROW = 7
    RANK_CHOICES = (
        (BOBCAT, "Bobcat"),
        (TIGER, "Tiger"),
        (WOLF, "Wolf"),
        (BEAR, "Bear"),
        (JR_WEBE, "Jr. Webelos"),
        (SR_WEBE, "Sr. Webelos"),
        (ARROW, "Arrow of Light"),
    )
    rank = models.PositiveSmallIntegerField(choices=RANK_CHOICES)
    description = models.CharField(max_length=128, blank=True, null=True)
    patch = models.ImageField(upload_to='dens/rank', blank=True, null=True,)

    def __str__(self):
        return self.get_rank_display()

    class Meta:
        ordering = ['rank']
        verbose_name = _('Rank')
        verbose_name_plural = _('Ranks')

    @property
    def category(self):
        if self.rank < 1:
            # We shouldn't see this
            return None
        elif self.rank <= 4:
            # Bobcat - Bear
            return _('Animal')
        elif self.rank <= 6:
            # Jr. & Sr. Webelos
            return _('Webelos')
        else:
            return None


class Den(models.Model):
    """ Each cub should be a member of 1 den """

    number = models.PositiveSmallIntegerField(primary_key=True)
    rank = models.ForeignKey(Rank, on_delete=models.CASCADE, related_name='dens', blank=True, null=True)
    patch = models.ImageField(upload_to='dens', blank=True, null=True)

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        verbose_name = _('Den')
        verbose_name_plural = _('Dens')

    def __str__(self):
        return 'Den {}'.format(self.number)

    def get_absolute_url(self):
        return reverse('den_detail', args=[int(self.number)])
