from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.dens.factories import DenFactory, MembershipFactory
from packman.dens.models import Den
from packman.dens.views import DenDetailView, DensListView
from packman.membership.factories import CompleteFamilyFactory, ScoutFactory

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


class DenDetailNewCubBadgeTestCase(TestCase):
    """
    The "New" badge beside a Cub's name on the den roster.

    A Cub is new to the pack when their earliest den assignment is the current
    Pack Year. A Cub returning for another year carries an older assignment, so
    the badge has to disappear for them - that is the case worth guarding.
    """

    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        # Leaving the dates unset lets PackYear.save() derive the real window,
        # so the prior year cannot overlap today and make current() ambiguous.
        cls.previous_year = PackYearFactory(year=cls.year.year - 1, start_date=None, end_date=None)
        cls.den = DenFactory()

        cls.viewer_family = CompleteFamilyFactory(adults=1, active_children=1)
        cls.viewer = cls.viewer_family.adults.first()

        cls.new_cub = ScoutFactory(first_name="Newton", last_name="Newcomer")
        MembershipFactory(scout=cls.new_cub, den=cls.den, year_assigned=cls.year)

        cls.returning_cub = ScoutFactory(first_name="Rhoda", last_name="Returning")
        MembershipFactory(scout=cls.returning_cub, den=cls.den, year_assigned=cls.previous_year)
        MembershipFactory(scout=cls.returning_cub, den=cls.den, year_assigned=cls.year)

        cls.url = reverse("dens:detail", kwargs={"pk": cls.den.pk})

    def setUp(self):
        # PackYearManager.current() memoises under the `current_year` key, and a
        # stale entry would silently decide every Cub is a returning one.
        cache.clear()
        self.client.force_login(self.viewer)

    def is_new_by_scout(self, response):
        return {row["scout"]: row["is_new"] for row in response.context["cubs"]}

    def test_first_year_cub_is_flagged(self):
        response = self.client.get(self.url)

        self.assertIs(self.is_new_by_scout(response)[self.new_cub], True)

    def test_returning_cub_is_not_flagged(self):
        response = self.client.get(self.url)

        self.assertIs(self.is_new_by_scout(response)[self.returning_cub], False)

    def test_badge_renders_once_for_a_mixed_den(self):
        response = self.client.get(self.url)

        self.assertContains(response, "badge text-bg-info", count=1)

    def test_badge_is_absent_when_every_cub_is_returning(self):
        self.new_cub.den_memberships.filter(year_assigned=self.year).update(year_assigned=self.previous_year)
        MembershipFactory(scout=self.new_cub, den=self.den, year_assigned=self.year)

        response = self.client.get(self.url)

        self.assertNotContains(response, "badge text-bg-info")
