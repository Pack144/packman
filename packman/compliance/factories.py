from django.utils import timezone

import factory

from packman.calendars.factories import CurrentPackYearFactory
from packman.compliance.models import Requirement, RequirementRecord


class RequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Requirement
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Requirement {n}")
    slug = factory.Sequence(lambda n: f"requirement-{n}")
    applies_to = Requirement.Audience.CUB
    tracks_expiration = True


class CubRequirementFactory(RequirementFactory):
    applies_to = Requirement.Audience.CUB


class AdultRequirementFactory(RequirementFactory):
    applies_to = Requirement.Audience.ADULT


class FamilyRequirementFactory(RequirementFactory):
    applies_to = Requirement.Audience.FAMILY
    tracks_expiration = False


class RequirementRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RequirementRecord

    requirement = factory.SubFactory(CubRequirementFactory)
    year = factory.SubFactory(CurrentPackYearFactory)
    member = factory.SubFactory("packman.membership.factories.ActiveScoutFactory")


class CompleteRecordFactory(RequirementRecordFactory):
    status = RequirementRecord.Status.COMPLETE
    completed_on = factory.LazyFunction(timezone.localdate)
    expires_on = factory.LazyFunction(lambda: timezone.localdate() + timezone.timedelta(days=365))


class ExpiringRecordFactory(CompleteRecordFactory):
    expires_on = factory.LazyFunction(lambda: timezone.localdate() + timezone.timedelta(days=30))


class ExpiredRecordFactory(CompleteRecordFactory):
    completed_on = factory.LazyFunction(lambda: timezone.localdate() - timezone.timedelta(days=400))
    expires_on = factory.LazyFunction(lambda: timezone.localdate() - timezone.timedelta(days=1))
