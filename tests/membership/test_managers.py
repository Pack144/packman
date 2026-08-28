from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.dens.factories import MembershipFactory
from packman.membership.factories import (
    ActiveScoutFactory,
    CompleteFamilyFactory,
    FamilyFactory,
    ScoutFactory,
)
from packman.membership.models import Adult, Family, Scout

User = get_user_model()


class AdultManagersTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(email="normal@example.com", password="foo")  # nosec B106
        self.assertEqual(user.email, "normal@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user._is_staff)
        self.assertFalse(user.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_user()
        with self.assertRaises(ValueError):
            User.objects.create_user(email="")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="foo")  # nosec B106

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser("super@example.com", "foo")  # nosec B106
        self.assertEqual(admin_user.email, "super@example.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user._is_staff)
        self.assertTrue(admin_user.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="super@user.com", password="foo", is_superuser=False)  # nosec B106

    def test_get_by_natural_key_is_case_insensitive(self):
        member = Adult.objects.create_user(
            email="member@example.com",
            password="Be Prepared",  # nosec: B106
        )

        self.assertEqual(Adult.objects.get_by_natural_key(username="member@example.com"), member)
        self.assertEqual(Adult.objects.get_by_natural_key(username="MEMBER@example.com"), member)
        self.assertEqual(Adult.objects.get_by_natural_key(username="member@EXAMPLE.COM"), member)
        self.assertEqual(Adult.objects.get_by_natural_key(username="MEMBER@EXAMPLE.COM"), member)
        self.assertEqual(Adult.objects.get_by_natural_key(username="Member@Example.com"), member)


class FamilyQuerySetTests(TestCase):
    """
    active() joins through children twice, so a family with more than one
    active Cub used to come back once per Cub.
    """

    def setUp(self):
        cache.clear()
        self.year = CurrentPackYearFactory()
        cache.clear()

    def test_family_with_several_active_cubs_appears_once(self):
        CompleteFamilyFactory(active_children=3)

        self.assertEqual(Family.objects.active_in(self.year).count(), 1)

    def test_active_in_accepts_a_year(self):
        CompleteFamilyFactory(active_children=1)

        self.assertEqual(Family.objects.active_in(self.year).count(), 1)

    def test_active_in_finds_nothing_in_an_unrelated_year(self):
        CompleteFamilyFactory(active_children=1)
        other = PackYearFactory(year=self.year.year - 5)

        self.assertEqual(Family.objects.active_in(other).count(), 0)

    def test_the_same_child_must_satisfy_both_conditions(self):
        """
        An inactive Cub with a den membership and an active sibling without one
        must not together make the family look active.
        """
        family = FamilyFactory()
        enrolled = ScoutFactory(family=family, status=Scout.APPROVED)
        MembershipFactory(scout=enrolled, year_assigned=self.year)
        ScoutFactory(family=family, status=Scout.ACTIVE)

        self.assertEqual(Family.objects.active_in(self.year).count(), 0)


class ScoutQuerySetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.year = CurrentPackYearFactory()
        cache.clear()

    def test_active_in_accepts_a_year(self):
        ActiveScoutFactory()

        self.assertEqual(Scout.objects.active_in(self.year).count(), 1)

    def test_active_in_accepts_several_years(self):
        scout = ActiveScoutFactory()
        later = PackYearFactory(year=self.year.year + 1)
        MembershipFactory(scout=scout, den=scout.den_memberships.first().den, year_assigned=later)

        self.assertEqual(Scout.objects.active_in([self.year, later]).count(), 1)
