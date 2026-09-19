from django.test import TestCase
from django.urls import reverse

from packman.pages.models import Page


class PageTests(TestCase):
    def test_inline_cms_slug_gets_required_prefix(self):
        page = Page(title="News content", slug="news", nav_placement=Page.NavPlacement.INLINE_CMS)

        page.full_clean()

        self.assertEqual(page.slug, "cms-news")

    def test_generated_inline_cms_slug_gets_required_prefix(self):
        page = Page(title="Special Content", nav_placement=Page.NavPlacement.INLINE_CMS)

        page.full_clean()

        self.assertEqual(page.slug, "cms-special-content")

    def test_inline_cms_absolute_url_opens_admin_editor(self):
        page = Page.objects.create(
            title="Home content",
            slug="cms-test-home",
            nav_placement=Page.NavPlacement.INLINE_CMS,
        )

        self.assertEqual(page.get_absolute_url(), reverse("admin:pages_page_change", args=(page.pk,)))
