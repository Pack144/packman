import datetime

from django.contrib.messages.storage.cookie import CookieStorage
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.calendars.models import PackYear
from packman.compliance.factories import CubRequirementFactory, RequirementRecordFactory
from packman.compliance.models import RequirementRecord
from packman.compliance.summaries import count_needs_attention, summarize_family
from packman.membership.factories import ActiveScoutFactory, AdultFactory, CompleteFamilyFactory, ScoutFactory
from packman.membership.models import Adult
from packman.pages.models import ContentBlock, Page
from packman.pages.views import HomePageView, PageDetailView, SignUpPageView


class AboutPageTests(TestCase):
    def setUp(self):
        self.page = Page.objects.create(title="About Us", slug="about", nav_placement=Page.NavPlacement.ABOUT)
        ContentBlock.objects.create(page=self.page, body="<p>About us.</p>", visibility=ContentBlock.Visibility.PUBLIC)
        self.response = self.client.get(reverse("pages:detail", kwargs={"slug": "about"}))

    def test_aboutpage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_aboutpage_template(self):
        self.assertTemplateUsed(self.response, "pages/page_detail.html")

    def test_aboutpage_url_resolves_pagedetailview(self):
        view = resolve("/about/")
        self.assertEqual(view.func.__name__, PageDetailView.as_view().__name__)


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
        self.page = Page.objects.create(title="Our History", slug="history", nav_placement=Page.NavPlacement.ABOUT)
        ContentBlock.objects.create(
            page=self.page, body="<p>Our history.</p>", visibility=ContentBlock.Visibility.PUBLIC
        )
        self.response = self.client.get(reverse("pages:detail", kwargs={"slug": "history"}))

    def test_historypage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_historypage_template(self):
        self.assertTemplateUsed(self.response, "pages/page_detail.html")

    def test_historypage_url_resolves_pagedetailview(self):
        view = resolve("/history/")
        self.assertEqual(view.func.__name__, PageDetailView.as_view().__name__)


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
        # The banner counts registrations too, so the Cubs start registered.
        # These tests are about what the records contribute; the registration
        # cases below clear a registration to say so explicitly.
        for cub in self.family.children.all():
            self.register(cub, timezone.localdate() + datetime.timedelta(days=200))

    @staticmethod
    def register(cub, expires_on, membership_id="137042891"):
        cub.scouting_membership_id = membership_id
        cub.scouting_membership_expires_on = expires_on
        cub.save()

    def record(self, **kwargs):
        return RequirementRecordFactory(
            requirement=self.requirement,
            year=self.year,
            member=self.family.children.first(),
            **kwargs,
        )

    def notice(self, response):
        return [m for m in response.context["messages"] if "attention" in str(m)]

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

        self.assertIn("1 membership item needs attention", str(self.notice(response)[0]))

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

    def test_a_cub_with_no_registration_raises_the_notice(self):
        """The gap that started this: registrations count, records or not."""
        self.register(self.family.children.first(), None, membership_id="")
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertIn("1 membership item needs attention", str(self.notice(response)[0]))

    def test_a_registration_lapsing_soon_counts(self):
        """The family page warns ahead of the date, so the banner does too."""
        self.register(self.family.children.first(), timezone.localdate() + datetime.timedelta(days=30))
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertIn("1 membership item needs attention", str(self.notice(response)[0]))

    def test_a_departed_siblings_registration_is_not_counted(self):
        """Nobody is asking a Cub who has left the pack to renew."""
        ScoutFactory(family=self.family)
        self.client.force_login(self.parent)

        response = self.client.get(self.url)

        self.assertEqual(self.notice(response), [])

    def test_the_banner_agrees_with_the_my_requirements_page(self):
        """
        The two counts drifted apart once already. Records and a registration
        together, so a difference in either source would show up here.
        """
        self.record()
        self.register(self.family.children.last(), None, membership_id="")

        self.assertEqual(
            count_needs_attention(self.family.pk, self.year),
            summarize_family(self.family, self.year)["needs_attention"],
        )

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
