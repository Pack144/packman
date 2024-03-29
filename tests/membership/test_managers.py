from django.contrib.auth import get_user_model
from django.test import TestCase

from packman.membership.models import Adult

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
