import factory

from packman.calendars.factories import CurrentPackYearFactory
from packman.committees.models import Committee, CommitteeMember


class CommitteeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Committee
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Committee {n}")
    slug = factory.Sequence(lambda n: f"committee-{n}")


class LeadershipCommitteeFactory(CommitteeFactory):
    """A committee flagged as Pack Leadership, e.g. the one holding the Akelas."""

    name = "Pack Leadership"
    slug = "pack-leadership"
    leadership = True


class CommitteeMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CommitteeMember

    year = factory.SubFactory(CurrentPackYearFactory)
    committee = factory.SubFactory(CommitteeFactory)
    member = factory.SubFactory("packman.membership.factories.AdultFactory")


class AkelaFactory(CommitteeMemberFactory):
    committee = factory.SubFactory(LeadershipCommitteeFactory)
    position = CommitteeMember.Position.AKELA


class AssistantAkelaFactory(CommitteeMemberFactory):
    committee = factory.SubFactory(LeadershipCommitteeFactory)
    position = CommitteeMember.Position.ASSISTANT_AKELA


class DenLeaderFactory(CommitteeMemberFactory):
    committee = factory.SubFactory(LeadershipCommitteeFactory)
    position = CommitteeMember.Position.DEN_LEADER
