from django.db import models

from packman.calendars.models import PackYear


class RequirementQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_audience(self, audience):
        return self.filter(applies_to=audience)


class RequirementRecordQuerySet(models.QuerySet):
    def for_year(self, year=None):
        return self.filter(year=year or PackYear.objects.current())

    def for_family(self, family):
        return self.filter(family=family)

    def cubs(self):
        return self.filter(requirement__applies_to=self.model.requirement.field.related_model.Audience.CUB)

    def adults(self):
        return self.filter(requirement__applies_to=self.model.requirement.field.related_model.Audience.ADULT)

    def families(self):
        return self.filter(requirement__applies_to=self.model.requirement.field.related_model.Audience.FAMILY)

    def complete(self):
        return self.filter(status=self.model.Status.COMPLETE)

    def outstanding(self):
        """Nothing recorded yet. Waived records are deliberately excluded."""
        return self.filter(status=self.model.Status.NOT_STARTED)

    def waived(self):
        return self.filter(status=self.model.Status.WAIVED)
