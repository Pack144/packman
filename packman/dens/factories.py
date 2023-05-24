import factory

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.dens.models import Den, Membership


class DenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Den
        django_get_or_create = ("number",)

    number = factory.Sequence(lambda n: n + 1)


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    scout = factory.SubFactory("packman.membership.factories.ScoutFactory")
    den = factory.SubFactory(DenFactory)
    year_assigned = factory.SubFactory(PackYearFactory)


class CurrentMembershipFactory(MembershipFactory):
    year_assigned = factory.SubFactory(CurrentPackYearFactory)
