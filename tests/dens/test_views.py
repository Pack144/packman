from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse

from packman.dens.models import Den
from packman.dens.views import DenDetailView, DensListView

User = get_user_model()


class DenListViewTestCase(TestCase):
    url = reverse("dens:list")
    view = DensListView

    @classmethod
    def setUpTestData(cls):
        for i in range(1, 10):
            Den.objects.create(number=i)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", first_name="Test", last_name="User", password="foo"  # nosec B106
        )
        self.user.active = Mock(return_value=True)

    def test_view_url_resolves(self):
        view = resolve("/dens/")
        self.assertEqual(view.func.__name__, self.view.as_view().__name__)

    def test_view_redirects_to_login_when_anonymous(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        response = self.view.as_view()(request)

        self.assertEqual(response.status_code, 302)

    def test_view_status_code(self):
        request = self.factory.get(self.url)
        request.user = self.user
        response = self.view.as_view()(request)

        self.assertEqual(response.status_code, 200)


class DenDetailViewTestCase(TestCase):
    kwargs = {"pk": 1}
    url = reverse("dens:detail", kwargs=kwargs)
    view = DenDetailView

    @classmethod
    def setUpTestData(cls):
        for i in range(1, 10):
            Den.objects.create(number=i)

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", first_name="Test", last_name="User", password="foo"  # nosec B106
        )
        self.user.active = Mock(return_value=True)

    def test_view_url_resolves(self):
        view = resolve("/dens/1/")
        self.assertEqual(view.func.__name__, self.view.as_view().__name__)

    def test_view_redirects_to_login_when_anonymous(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        response = self.view.as_view()(request, **self.kwargs)

        self.assertEqual(response.status_code, 302)

    def test_view_status_code(self):
        request = self.factory.get(self.url)
        request.user = self.user
        response = self.view.as_view()(request, **self.kwargs)

        self.assertEqual(response.status_code, 200)
