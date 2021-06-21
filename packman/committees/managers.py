from django.db import models

from packman.calendars.models import PackYear


class CommitteeQuerySet(models.QuerySet):

    def by_year(self, year):
        """ Return a list of committees with members assigned for a given Pack Year. """
        return self.filter(membership__year_served=year)

    def by_years(self, years):
        """ Return a list of committees with members assigned for a list of Pack Years. """
        return self.filter(membership__year_served__in=years).distinct()

    def current(self):
        """ Return a list of committees with members assigned for the current Pack Year. """
        return self.by_year(year=PackYear.objects.current())

    def recent(self):
        """
        Return a list of committees with members assigned for the current Pack Year
        plus the years immediately before and after.
        """
        return self.by_years(years=PackYear.objects.recent())
