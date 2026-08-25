from django.urls import reverse

from packman.membership.factories import AdultFactory, FamilyFactory
from packman.membership.models import Adult

from .base import MobileDirectoryTestCase


class AppShellViewTestCase(MobileDirectoryTestCase):
    url = reverse("mobile:index")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_inactive_member_is_denied(self):
        parent = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)
        self.client.force_login(parent)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_active_member_can_load_the_shell(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mobile/index.html")

    def test_contributor_can_load_the_shell_without_active_cubs(self):
        contributor = AdultFactory(family=FamilyFactory(), role=Adult.CONTRIBUTOR)
        self.client.force_login(contributor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class ServiceWorkerAndManifestTestCase(MobileDirectoryTestCase):
    def test_service_worker_is_public_and_javascript(self):
        response = self.client.get(reverse("mobile:service-worker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertIn(b"pack-directory-shell", response.content)

    def test_manifest_is_public_and_json(self):
        response = self.client.get(reverse("mobile:manifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        self.assertIn(b'"display": "standalone"', response.content)
