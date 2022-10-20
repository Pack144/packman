from django.db import models
from django.db.models import Count, Q

from packman.calendars.models import PackYear


class DenQuerySet(models.QuerySet):
    def active_in(self, year):
        if hasattr(year, "__iter__"):
            qs = self.filter(scouts__year_assigned__in=year)
        else:
            qs = self.filter(scouts__year_assigned=year)
        return qs.distinct()

    def current(self):
        return self.active_in(year=PackYear.objects.current())

    def animals(self):
        return self.filter(rank__rank__lte=self.model.rank.field.related_model.RankChoices.BEAR)

    def webelos(self):
        return self.filter(rank__rank__gte=self.model.rank.field.related_model.RankChoices.JR_WEBE)

    def counting_members(self):
        return self.annotate(
            current_count=Count("scouts", filter=Q(scouts__year_assigned=PackYear.objects.current())),
            upcoming_count=Count("scouts", filter=Q(scouts__year_assigned=PackYear.objects.next())),
        )
