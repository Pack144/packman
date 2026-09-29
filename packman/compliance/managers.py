from django.apps import apps
from django.db import models
from django.db.models import Q

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

    def in_dens(self, year):
        """
        Records for the people the pack's dens hold in a pack year: Cubs active
        in a den, the adults in those Cubs' families, and the families' own
        records.

        Leaves out records left behind by someone who has since gone -- a Cub
        who withdrew part way through, or a household with no active Cub left
        -- and those of Friends of the Pack, who belong to no den.
        """
        family_model = apps.get_model("membership", "Family")
        scout_model = apps.get_model("membership", "Scout")
        return self.filter(year=year, family__in=family_model.objects.active_in(year).values("pk")).filter(
            # A household record, an adult's, or an active Cub's -- but not a
            # withdrawn sibling's, whose family is still active through another.
            Q(member__isnull=True)
            | Q(member__scout__isnull=True)
            | Q(member__in=scout_model.objects.active_in(year).values("pk"))
        )

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
