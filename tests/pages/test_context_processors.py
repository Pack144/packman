from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone

from packman.calendars.factories import PackYearFactory
from packman.campaigns.models import Campaign
from packman.membership.factories import AdultFactory
from packman.pages.context_processors import populate_navbar
from packman.pages.models import ContentBlock, Page


def _public_page(*, title, slug, nav_placement, order=0):
    page = Page.objects.create(title=title, slug=slug, nav_placement=nav_placement, order=order)
    ContentBlock.objects.create(page=page, body=f"<p>{title}</p>", visibility=ContentBlock.Visibility.PUBLIC)
    return page


class PopulateNavbarTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.pinned_page = _public_page(title="Trackers", slug="trackers", nav_placement=Page.NavPlacement.PINNED)
        self.about_page = _public_page(title="Our History", slug="history", nav_placement=Page.NavPlacement.ABOUT)
        self.pack_info_page = _public_page(
            title="Newsletter", slug="newsletter", nav_placement=Page.NavPlacement.PACK_INFO
        )
        self.hidden_page = _public_page(title="Draft", slug="draft", nav_placement=None)

    def _navbar(self, user):
        request = self.factory.get("/")
        request.user = user
        request.resolver_match = None
        return populate_navbar(request)

    def _dropdown(self, navbar_items, nav_id):
        return next(item for item in navbar_items if item.get("id") == nav_id)

    def test_pinned_page_is_a_top_level_link_for_authenticated_users(self):
        navbar = self._navbar(AdultFactory())

        top_level_labels = [item["label"] for item in navbar["navbar_items"] if item["kind"] == "link"]

        self.assertIn("Trackers", top_level_labels)

    def test_about_page_appears_in_the_about_dropdown(self):
        navbar = self._navbar(AdultFactory())

        about = self._dropdown(navbar["navbar_items"], "navbarAboutDropdown")

        self.assertIn("Our History", [item["label"] for item in about["items"]])

    def test_pack_info_page_appears_in_the_pack_info_dropdown(self):
        navbar = self._navbar(AdultFactory())

        pack_info = self._dropdown(navbar["navbar_items"], "navbarPackInfoDropdown")

        self.assertIn("Newsletter", [item["label"] for item in pack_info["items"]])

    def test_page_without_placement_is_excluded_from_nav_entirely(self):
        navbar = self._navbar(AdultFactory())

        all_labels = [item["label"] for item in navbar["navbar_items"] if item["kind"] == "link"]
        all_labels += [
            sub["label"] for item in navbar["navbar_items"] if item["kind"] == "dropdown" for sub in item["items"]
        ]

        self.assertNotIn("Draft", all_labels)

    def test_pinned_and_about_pages_are_grouped_for_anonymous_users(self):
        navbar = self._navbar(AnonymousUser())

        labels = [item["label"] for item in navbar["navbar_items"]]

        self.assertIn("Trackers", labels)
        self.assertIn("Our History", labels)
        self.assertIn("Newsletter", labels)
        self.assertNotIn("Draft", labels)

    def test_ordering_within_a_group_follows_the_order_field(self):
        second_about_page = _public_page(
            title="Membership Requirements",
            slug="membership-requirements",
            nav_placement=Page.NavPlacement.ABOUT,
            order=self.about_page.order + 1,
        )

        navbar = self._navbar(AdultFactory())

        about = self._dropdown(navbar["navbar_items"], "navbarAboutDropdown")
        about_labels = [item["label"] for item in about["items"]]

        self.assertLess(
            about_labels.index(self.about_page.title),
            about_labels.index(second_about_page.title),
        )

    def test_all_ncc_placed_pages_appear_in_the_ncc_dropdown(self):
        today = timezone.now()
        Campaign.objects.create(
            year=PackYearFactory(),
            ordering_opens=today - timezone.timedelta(days=1),
            ordering_closes=today + timezone.timedelta(days=29),
            delivery_available=today + timezone.timedelta(days=45),
            prize_window_opens=today + timezone.timedelta(days=45),
            prize_window_closes=today + timezone.timedelta(days=60),
        )
        first_ncc_page = _public_page(title="NCC Info", slug="nccinfo", nav_placement=Page.NavPlacement.NCC)
        second_ncc_page = _public_page(
            title="NCC FAQ", slug="ncc-faq", nav_placement=Page.NavPlacement.NCC, order=first_ncc_page.order + 1
        )

        navbar = self._navbar(AdultFactory())

        ncc = self._dropdown(navbar["navbar_items"], "navbarNccDropdown")
        ncc_labels = [item["label"] for item in ncc["items"]]

        self.assertIn(first_ncc_page.title, ncc_labels)
        self.assertIn(second_ncc_page.title, ncc_labels)
