from django.test import TestCase
from django.urls import reverse

from unfold.widgets import UnfoldAdminPasswordWidget

from packman.membership.factories import AdultFactory
from packman.membership.forms import AdminAdultCreation, AdultCreation
from packman.membership.models import Adult


class AdultAdminTests(TestCase):
    def setUp(self):
        self.user = AdultFactory(_is_staff=True, is_superuser=True)
        self.client.force_login(self.user)

    def test_public_creation_form_keeps_its_original_widgets(self):
        self.assertIsInstance(AdminAdultCreation.base_fields["password1"].widget, UnfoldAdminPasswordWidget)
        self.assertNotIsInstance(AdultCreation.base_fields["password1"].widget, UnfoldAdminPasswordWidget)

    def test_admin_can_create_an_adult(self):
        url = reverse("admin:membership_adult_add")
        response = self.client.get(url)
        data = {
            "first_name": "Test",
            "last_name": "Adult",
            "gender": "M",
            "email": "new-adult@example.com",
            "password1": "Unfold-Test-Password-459!",
            "password2": "Unfold-Test-Password-459!",
            "_save": "Save",
        }
        for inline in response.context["inline_admin_formsets"]:
            prefix = inline.formset.prefix
            data[f"{prefix}-TOTAL_FORMS"] = 0
            data[f"{prefix}-INITIAL_FORMS"] = 0
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, response.context and response.context["adminform"].form.errors)
        user = Adult.objects.get(email="new-adult@example.com")
        self.assertTrue(user.check_password(data["password1"]))
        self.assertFalse(user.is_superuser)

    def test_admin_password_change(self):
        other = AdultFactory()
        url = reverse("admin:auth_user_password_change", args=[other.pk])
        response = self.client.get(url)
        self.assertContains(response, "unfold/css/styles.css")
        response = self.client.post(
            url, {"password1": "Unfold-Test-Password-459!", "password2": "Unfold-Test-Password-459!"}
        )
        self.assertEqual(response.status_code, 302)
        other.refresh_from_db()
        self.assertTrue(other.check_password("Unfold-Test-Password-459!"))

    def test_admin_change_keeps_account_fields_and_inlines(self):
        response = self.client.get(reverse("admin:membership_adult_change", args=[self.user.pk]))
        self.assertContains(response, 'id="adult_form"')
        fields = response.context["adminform"].form.fields
        for name in ("password", "is_active", "_is_staff", "is_superuser", "groups", "user_permissions"):
            self.assertIn(name, fields)
        self.assertEqual(len(response.context["inline_admin_formsets"]), 4)
