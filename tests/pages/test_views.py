from django.contrib.messages.storage.cookie import CookieStorage
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.calendars.models import PackYear
from packman.compliance.factories import CubRequirementFactory, RequirementRecordFactory
from packman.compliance.models import RequirementRecord
from packman.membership.factories import ActiveScoutFactory, AdultFactory, CompleteFamilyFactory
from packman.membership.models import Adult
from packman.pages.views import AboutPageView, HistoryPageView, HomePageView, SignUpPageView


class AboutPageTests(TestCase):
    def setUp(self):
        url = reverse("pages:about")
        self.response = self.client.get(url)

    def test_aboutpage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_aboutpage_template(self):
        self.assertTemplateUsed(self.response, "pages/about_page.html")

    def test_aboutpage_url_resolves_aboutpageview(self):
        view = resolve("/about/")
        self.assertEqual(view.func.__name__, AboutPageView.as_view().__name__)


class HomePageTests(TestCase):
    def setUp(self):
        url = reverse("pages:home")
        self.response = self.client.get(url)

    def test_homepage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_homepage_template(self):
        self.assertTemplateUsed(self.response, "pages/home_page.html")

    def test_homepage_url_resolves_homepageview(self):  # new
        view = resolve("/")
        self.assertEqual(view.func.__name__, HomePageView.as_view().__name__)


class HistoryPageTests(TestCase):
    def setUp(self):
        url = reverse("pages:history")
        self.response = self.client.get(url)

    def test_historypage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_historypage_template(self):
        self.assertTemplateUsed(self.response, "pages/history_page.html")

    def test_historypage_url_resolves_historypageview(self):
        view = resolve("/history/")
        self.assertEqual(view.func.__name__, HistoryPageView.as_view().__name__)


class SignUpPageTests(TestCase):
    def setUp(self):
        url = reverse("pages:signup")
        self.response = self.client.get(url)

    def test_signuppage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_signuppage_template(self):
        self.assertTemplateUsed(self.response, "pages/signup_page.html")

    def test_signuppage_url_resolves_signuppageview(self):
        view = resolve("/signup/")
        self.assertEqual(view.func.__name__, SignUpPageView.as_view().__name__)


class HomePageRequirementsNoticeTests(TestCase):
    """
    The nudge telling a family the pack is still waiting on paperwork, and
    sending them to the page that says which.
    """

    def setUp(self):
        cache.clear()
        self.url = reverse("pages:home")
        self.year = CurrentPackYearFactory()
        self.family = CompleteFamilyFactory(adults=1, active_children=2)
        self.parent = self.family.adults.first()
        self.requirement = CubRequirementFactory(slug="home-notice")

    def record(self, **kwargs):
        return RequirementRecordFactory(
            requirement=self.requirement,
            year=self.year,
            member=self.family.children.first(),
            **kwargs,
        )

    def notice(self, response):
        return [m for m in response.context["messages"] if "requirement" in str(m)]

    def test_outstanding_paperwork_raises_a_notice(self):
        self.record()
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertEqual(len(self.notice(response)), 1)
        self.assertContains(response, reverse("compliance:my_family"))

    def test_the_notice_counts_only_what_is_outstanding(self):
        self.record()
        RequirementRecordFactory(
            requirement=self.requirement,
            year=self.year,
            member=self.family.children.last(),
            status=RequirementRecord.Status.COMPLETE,
        )
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertIn("1 membership requirement needs attention", str(self.notice(response)[0]))

    def test_nothing_outstanding_is_silent(self):
        self.record(status=RequirementRecord.Status.COMPLETE)
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertEqual(self.notice(response), [])

    def test_a_waived_record_is_not_outstanding(self):
        self.record(status=RequirementRecord.Status.WAIVED)
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertEqual(self.notice(response), [])

    def test_another_familys_paperwork_is_not_reported(self):
        RequirementRecordFactory(requirement=self.requirement, year=self.year, member=ActiveScoutFactory())
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertEqual(self.notice(response), [])

    def test_anonymous_visitors_see_no_notice(self):
        self.record()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.notice(response), [])

    def test_a_member_without_a_family_does_not_break_the_page(self):
        self.record()
        self.client.force_login(AdultFactory(family=None, role=Adult.CONTRIBUTOR))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.notice(response), [])

    def test_the_banner_is_skipped_when_the_current_year_is_ambiguous(self):
        """
        A stray overlapping year makes PackYear.objects.current() raise. Other
        parts of the page (committee lookups behind user.is_staff) still fall
        over, and deliberately so, but the banner must not be what breaks.
        """
        self.record()
        now = timezone.now()
        # An unused year value, but dates that overlap today, which is what
        # makes objects.current() ambiguous.
        PackYear.objects.create(
            year=now.year + 50,
            start_date=now - timezone.timedelta(days=5),
            end_date=now + timezone.timedelta(days=300),
        )
        cache.clear()

        request = RequestFactory().get(reverse("pages:home"))
        request.user = self.parent
        request._messages = CookieStorage(request)
        view = HomePageView()
        view.request = request

        view.notify_outstanding_requirements()

        self.assertEqual(list(request._messages), [])
