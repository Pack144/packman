from django.db.models import Case, CharField, QuerySet, Value, When

from packman.calendars.models import PackYear

from .derived import status_q

EFFECTIVE_STATUS = "_effective_status"


class RequirementQuerySet(QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_audience(self, audience):
        return self.filter(applies_to=audience)

    def derived(self):
        return self.exclude(source=self.model.Source.MANUAL)


class RequirementRecordQuerySet(QuerySet):
    def for_year(self, year=None):
        return self.filter(year=year or PackYear.objects.current())

    def for_family(self, family):
        return self.filter(family=family)

    def _audience(self, audience):
        return self.filter(requirement__applies_to=audience)

    def cubs(self):
        return self._audience(self.model.requirement.field.related_model.Audience.CUB)

    def adults(self):
        return self._audience(self.model.requirement.field.related_model.Audience.ADULT)

    def leaders(self):
        return self._audience(self.model.requirement.field.related_model.Audience.LEADER)

    def families(self):
        return self._audience(self.model.requirement.field.related_model.Audience.FAMILY)

    def with_effective_status(self, as_of=None):
        """
        Annotate what each record reads as today, the SQL twin of
        RequirementRecord.effective_status.

        A derived requirement's standing is not in its own status column, so
        filtering that column directly would report a lapsed registration as
        complete.
        """
        if EFFECTIVE_STATUS in self.query.annotations:
            return self

        Status = self.model.Status
        return self.annotate(
            **{
                EFFECTIVE_STATUS: Case(
                    *(
                        When(
                            status_q(status, prefix="", source_prefix="requirement__", as_of=as_of), then=Value(status)
                        )
                        # Waived is tested first so it outranks the rest, the
                        # same precedence effective_status applies.
                        for status in (Status.WAIVED, Status.COMPLETE, Status.EXPIRED)
                    ),
                    default=Value(Status.NOT_STARTED),
                    output_field=CharField(),
                )
            }
        )

    def at_status(self, *statuses, as_of=None):
        return self.with_effective_status(as_of).filter(**{f"{EFFECTIVE_STATUS}__in": statuses})

    def complete(self, as_of=None):
        return self.at_status(self.model.Status.COMPLETE, as_of=as_of)

    def expired(self, as_of=None):
        return self.at_status(self.model.Status.EXPIRED, as_of=as_of)

    def outstanding(self, as_of=None):
        """
        Nothing recorded yet, or a membership that has lapsed. Waived records
        are deliberately excluded.
        """
        return self.at_status(self.model.Status.NOT_STARTED, self.model.Status.EXPIRED, as_of=as_of)

    def waived(self):
        return self.filter(status=self.model.Status.WAIVED)
