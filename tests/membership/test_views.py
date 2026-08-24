from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from packman.calendars.models import PackYear
from packman.committees.leadership import is_pack_leader
from packman.committees.models import Committee, CommitteeMember
from packman.dens.factories import DenFactory
from packman.dens.models import Membership
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory
from packman.membership.models import Scout

User = get_user_model()


class MemberListTestCase(TestCase):
    pass


class MemberSearchResultsTestCase(TestCase):
    pass


class AdultListTestCase(TestCase):
    pass


class AdultCreateTestCase(TestCase):
    pass


class AdultDetailTestCase(TestCase):
    pass


class AdultUpdateTestCase(TestCase):
    pass


class ScoutListTestCase(TestCase):
    pass


class ScoutCreateTestCase(TestCase):
    pass


class ScoutDetailTestCase(TestCase):
    pass


class ScoutUpdateTestCase(TestCase):
    pass


class MyFamilyDetailTestCase(TestCase):
    pass


class PackMateEntryPointsTestCase(TestCase):
    """Both routes into PackMate should open only to those the app would let in."""

    # Every page that mirrors what the app shows, and so carries the promo.
    DIRECTORY_URLS = (
        "membership:scouts",
        "membership:parents",
        "membership:all",
        "dens:list",
    )

    @classmethod
    def setUpTestData(cls):
        end_year = PackYear.get_pack_year()["end_date"].year
        cls.pack_year, _ = PackYear.objects.get_or_create(year=end_year)
        cls.committee = Committee.objects.create(name="Pack Leadership", slug="pack-leadership", leadership=True)

        cls.den = DenFactory()

        # A den leader with an active cub: sees PackMate everywhere.
        cls.leader = AdultFactory(family=cls.active_family())
        cls.assign(cls.leader, CommitteeMember.Position.DEN_LEADER)

        # An ordinary parent: can reach the directory, but PackMate is pitched
        # at the leaders who run dens, so it stays hidden from them.
        cls.parent = AdultFactory(family=cls.active_family())

        # A den leader whose own cubs have aged out: leads a den, but PackMate
        # itself would turn them away, so we don't advertise it.
        cls.former_parent = AdultFactory(family=FamilyFactory())
        cls.assign(cls.former_parent, CommitteeMember.Position.DEN_LEADER)

    @classmethod
    def active_family(cls):
        """
        A family with one active cub in a den.

        Built by hand rather than with ActiveScoutFactory: that reaches for
        CurrentPackYearFactory, which lays down a calendar-year PackYear
        overlapping the pack-year row migrations create. Two rows covering
        today make PackYear.objects.current()'s bare .get() raise.
        """
        family = FamilyFactory()
        scout = ScoutFactory(family=family, status=Scout.ACTIVE)
        Membership.objects.create(scout=scout, den=cls.den, year_assigned=cls.pack_year)
        return family

    @classmethod
    def assign(cls, member, position):
        return CommitteeMember.objects.create(
            committee=cls.committee, member=member, year=cls.pack_year, position=position
        )

    def setUp(self):
        # PackYear.objects.current() caches; clear it so the rows above are seen.
        cache.clear()

    def test_banner_shown_to_active_member(self):
        self.client.force_login(self.leader)
        for name in self.DIRECTORY_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "packmate-promo")
                self.assertContains(response, reverse("mobile:index"))

    def test_banner_hidden_from_ineligible_member(self):
        self.client.force_login(self.former_parent)
        response = self.client.get(reverse("membership:scouts"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "packmate-promo")

    def test_banner_absent_from_other_pages(self):
        self.client.force_login(self.leader)
        response = self.client.get(reverse("documents:list"))
        self.assertNotContains(response, "packmate-promo")

    def test_dropdown_link_shown_to_active_member(self):
        # The profile dropdown rides on every page, not just the directory ones.
        self.client.force_login(self.leader)
        response = self.client.get(reverse("documents:list"))
        self.assertContains(response, "packmate-icon")
        self.assertContains(response, reverse("mobile:index"))

    def test_dropdown_link_hidden_from_ineligible_member(self):
        # Documents 403s for them, so ask for a page they can actually reach.
        self.client.force_login(self.former_parent)
        response = self.client.get(reverse("membership:scouts"))
        self.assertNotContains(response, "packmate-icon")

    def test_dropdown_link_absent_when_signed_out(self):
        response = self.client.get(reverse("pages:home"))
        self.assertNotContains(response, "packmate-icon")

    def test_hidden_from_member_without_leadership_role(self):
        # Active cubs and full directory access, but leads nothing.
        self.client.force_login(self.parent)
        response = self.client.get(reverse("membership:scouts"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "packmate-promo")
        self.assertNotContains(response, "packmate-icon")

    def test_shown_to_akela_and_assistant_akela(self):
        for position in (
            CommitteeMember.Position.AKELA,
            CommitteeMember.Position.ASSISTANT_AKELA,
        ):
            with self.subTest(position=position.label):
                akela = AdultFactory(family=self.active_family())
                self.assign(akela, position)

                self.client.force_login(akela)
                response = self.client.get(reverse("membership:scouts"))
                self.assertContains(response, "packmate-promo")
                self.assertContains(response, "packmate-icon")

    def test_hidden_once_leadership_role_lapses(self):
        # Last year's den leader has no claim on this year's app.
        past_leader = AdultFactory(family=self.active_family())
        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        CommitteeMember.objects.create(
            committee=self.committee,
            member=past_leader,
            year=last_year,
            position=CommitteeMember.Position.DEN_LEADER,
        )

        self.client.force_login(past_leader)
        response = self.client.get(reverse("membership:scouts"))
        self.assertNotContains(response, "packmate-promo")

    def test_leadership_check_survives_an_undeterminable_pack_year(self):
        """
        is_pack_leader is asked on every page render, so it must swallow a Pack
        Year it can't pin down rather than raise. Here a second year overlaps
        today, which makes PackYear.objects.current()'s bare .get() blow up.

        Asserted against the helper rather than a rendered page: Adult.is_staff
        reaches for PackYear.objects.current() too, by way of
        CommitteeQuerySet.recent(), and takes the request down first.
        """
        PackYear.objects.create(
            year=self.pack_year.year + 50,
            start_date=self.pack_year.start_date,
            end_date=self.pack_year.end_date,
        )
        cache.clear()

        self.assertIs(is_pack_leader(self.leader), False)
