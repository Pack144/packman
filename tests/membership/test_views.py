from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from packman.calendars.models import PackYear
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
    """Both routes into PackMate are open to any signed-in member; no gate."""

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
        cls.den = DenFactory()

        # An ordinary parent with an active cub, no leadership role or
        # committee seat: still gets PackMate now that it's ungated.
        cls.member = AdultFactory(family=cls.active_family())

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

    def setUp(self):
        # PackYear.objects.current() caches; clear it so the rows above are seen.
        cache.clear()

    def test_banner_shown_to_signed_in_member(self):
        self.client.force_login(self.member)
        for name in self.DIRECTORY_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "packmate-promo")
                self.assertContains(response, reverse("mobile:index"))

    def test_banner_absent_from_other_pages(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:list"))
        self.assertNotContains(response, "packmate-promo")

    def test_dropdown_link_shown_to_signed_in_member(self):
        # The profile dropdown rides on every page, not just the directory ones.
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:list"))
        self.assertContains(response, "packmate-icon")
        self.assertContains(response, reverse("mobile:index"))

    def test_dropdown_link_absent_when_signed_out(self):
        response = self.client.get(reverse("pages:home"))
        self.assertNotContains(response, "packmate-icon")
