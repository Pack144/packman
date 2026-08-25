from django.core.cache import cache
from django.test import TestCase

from packman.calendars.models import PackYear
from packman.committees.models import Committee, CommitteeMember
from packman.dens.factories import DenFactory
from packman.dens.models import Membership, Rank
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory
from packman.membership.models import Adult, Scout


class MobileDirectoryTestCase(TestCase):
    """
    Builds a small, realistic directory: one active family (a parent + their
    cub, in a ranked den with a den leader) that tests can log in as.
    """

    @classmethod
    def setUpTestData(cls):
        # Get (rather than blindly create) the PackYear that contains "now":
        # an old committees migration's field default calls
        # PackYear.get_current_pack_year_year(), which as a side effect
        # already creates this exact row while the test DB's migrations run.
        end_year = PackYear.get_pack_year()["end_date"].year
        cls.pack_year, _ = PackYear.objects.get_or_create(year=end_year)
        cls.rank = Rank.objects.create(rank=Rank.RankChoices.WOLF)
        cls.den = DenFactory(rank=cls.rank)

        cls.family = FamilyFactory()
        cls.parent = AdultFactory(family=cls.family, role=Adult.PARENT, is_published=True)
        cls.scout = ScoutFactory(family=cls.family, status=Scout.ACTIVE)
        Membership.objects.create(scout=cls.scout, den=cls.den, year_assigned=cls.pack_year)

        committee = Committee.objects.create(name="Wolf Den", slug="wolf-den")
        cls.leader = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=cls.leader,
            den=cls.den,
            year=cls.pack_year,
            position=CommitteeMember.Position.DEN_LEADER,
        )

    def setUp(self):
        # PackYear.objects.current() caches its result; clear it so each test
        # sees the PackYear created by setUpTestData rather than a stale
        # instance left over by another test module.
        cache.clear()
