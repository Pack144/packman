from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory

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
        active_family = FamilyFactory()
        ActiveScoutFactory(family=active_family)
        cls.parent = AdultFactory(family=active_family)

        # A parent whose cubs have all aged out: still allowed to sign in and
        # reach the membership lists, but PackMate itself would turn them away.
        cls.former_parent = AdultFactory(family=FamilyFactory())

    def test_banner_shown_to_active_member(self):
        self.client.force_login(self.parent)
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
        self.client.force_login(self.parent)
        response = self.client.get(reverse("documents:list"))
        self.assertNotContains(response, "packmate-promo")

    def test_dropdown_link_shown_to_active_member(self):
        # The profile dropdown rides on every page, not just the directory ones.
        self.client.force_login(self.parent)
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
