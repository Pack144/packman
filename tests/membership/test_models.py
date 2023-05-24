from django.test import TestCase
from django.utils import timezone

from packman.membership.models import Member


class MemberTestCase(TestCase):
    def test_member_string(self):
        member = Member.objects.create(first_name="Test", last_name="Member")

        self.assertEqual(str(member), "Test Member")

    def test_member_string_with_nickname(self):
        member = Member.objects.create(first_name="Test", nickname="Awesome", last_name="Member")

        self.assertEqual(str(member), "Awesome Member")

    def test_member_string_with_middle_name(self):
        member = Member.objects.create(first_name="Test", middle_name="The", last_name="Member")

        self.assertEqual(str(member), "Test Member")

    def test_member_string_with_nickname_and_middle_name(self):
        member = Member.objects.create(first_name="Test", middle_name="The", nickname="Awesome", last_name="Member")

        self.assertEqual(str(member), "Awesome Member")

    def test_member_string_with_suffix(self):
        member = Member.objects.create(first_name="Test", last_name="Member", suffix="Jr.")

        self.assertEqual(str(member), "Test Member Jr.")

    def test_age(self):
        # TODO: age() is a function, update to property that calls a `get_age` function
        now = timezone.now()
        member1 = Member.objects.create(
            first_name="Young", last_name="Member", date_of_birth=now - timezone.timedelta(days=365.4 * 9.5)
        )
        member2 = Member.objects.create(
            first_name="Old", last_name="Member", date_of_birth=now - timezone.timedelta(days=365.4 * 45)
        )
        member3 = Member.objects.create(first_name="Unknown", last_name="Member")

        self.assertEqual(member1.age(), 9)
        self.assertEqual(member2.age(), 45)
        self.assertIsNone(member3.age())

    def test_member_valid_slug(self):
        member1 = Member.objects.create(first_name="First", last_name="Member")
        member2 = Member.objects.create(first_name="First", nickname="Real", last_name="Member")
        member3 = Member.objects.create(first_name="First", last_name="Member", suffix="III")
        member4 = Member.objects.create(first_name="First", middle_name="Test", last_name="Member")
        member5 = Member.objects.create(first_name="First", middle_name="Test", last_name="Member")
        member6 = Member.objects.create(first_name="First", last_name="Member")
        member7 = Member.objects.create(first_name="First", last_name="Member")
        member8 = Member.objects.create(first_name="First", last_name="Member")
        member9 = Member.objects.create(first_name="First", last_name="Member")

        self.assertEqual(member1.slug, "first-member")
        self.assertEqual(member2.slug, "real-member")
        self.assertEqual(member3.slug, "first-member-iii")
        self.assertEqual(member4.slug, "first-t-member")
        self.assertEqual(member5.slug, "first-test-member")
        self.assertEqual(member6.slug, "first-member-1")
        self.assertEqual(member7.slug, "first-member-2")
        self.assertEqual(member8.slug, "first-member-3")
        self.assertEqual(member9.slug, "first-member-4")

    def test_members_get_unique_slugs(self):
        for _ in range(100):
            Member.objects.create(first_name="Another", last_name="Member")
            Member.objects.create(first_name="Another", nickname="Wonderful", last_name="Member")
            Member.objects.create(first_name="Another", last_name="Member", suffix="2")


class AdultTestCase(TestCase):
    pass


class ScoutTestCase(TestCase):
    pass
