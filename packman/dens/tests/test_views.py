from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from packman.dens.models import Den
from packman.dens.views import DenDetailView, DensListView


class DenListViewTestCase(SimpleTestCase):
    def setUp(self):
        url = reverse("dens:list")
        self.response = self.client.get(url)

    def test_view_url_resolves(self):
        view = resolve("/dens/")
        self.assertEqual(view.func.__name__, DensListView.as_view().__name__)

    def test_view_redirects_to_login_when_anonymous(self):
        self.assertEqual(self.response.status_code, 302)
        self.assertRedirects(self.response, reverse("login") + "?next=/dens/")

    # TODO: Test with logged in active member
    # def test_view_status_code(self):
    #     self.assertEqual(self.response.status_code, 200)

    # TODO: Test with logged in active member
    # def test_view_template(self):
    #     self.assertTemplateUsed(self.response, "dens/den_list.html")


class DenDetailViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Den.objects.create(pk=1)

    def setUp(self):
        url = reverse("dens:detail", args=(1,))
        self.response = self.client.get(url)

    def test_view_url_resolves(self):
        view = resolve("/dens/1/")
        self.assertEqual(view.func.__name__, DenDetailView.as_view().__name__)

    def test_view_redirects_to_login_when_anonymous(self):
        self.assertEqual(self.response.status_code, 302)
        self.assertRedirects(self.response, reverse("login") + "?next=/dens/1/")

    # TODO: Test with logged in active member
    # def test_view_status_code(self):
    #     self.assertEqual(self.response.status_code, 200)

    # TODO: Test with logged in active member
    # def test_view_template(self):
    #     self.assertTemplateUsed(self.response, "dens/den_detail.html")
