from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Den(models.Model):
    """ Each cub should be a member of 1 den """
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

    number = models.PositiveSmallIntegerField(primary_key=True)
    rank = models.PositiveSmallIntegerField(choices=RANK_CHOICES, blank=True, null=True)

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return 'Den {}'.format(self.number)

    def get_absolute_url(self):
        return reverse('den_detail', args=[int(self.number)])

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
