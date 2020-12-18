from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class AdultManagersTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(email="normal@example.com", password="foo")
        self.assertEqual(user.email, "normal@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user._is_staff)
        self.assertFalse(user.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_user()
        with self.assertRaises(ValueError):
            User.objects.create_user(email="")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="foo")

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser("super@example.com", "foo")
        self.assertEqual(admin_user.email, "super@example.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user._is_staff)
        self.assertTrue(admin_user.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", is_superuser=False
            )
