from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from packman.membership.factories import AdultFactory
from packman.pages.admin import PageAdmin
from packman.pages.models import ContentBlock, Page


class PageAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AdultFactory(_is_staff=True, is_superuser=True)
        cls.pages = [
            Page.objects.create(title=f"Sort page {index}", slug=f"sort-page-{index}", order=index * 10)
            for index in range(1, 5)
        ]

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("admin:pages_page_changelist")

    def reorder(self, pages, query=None):
        data = {"_save": "Save", "form-TOTAL_FORMS": len(pages), "form-INITIAL_FORMS": len(pages)}
        for index, page in enumerate(pages):
            data[f"form-{index}-uuid"] = page.pk
            data[f"form-{index}-order"] = index
        url = f"{self.url}?{query}" if query else self.url
        return self.client.post(url, data)

    def test_native_sorting_renders_with_uuid_records(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'data-ordering-field="order"')
        self.assertNotContains(response, "adminsortable2")

    def test_reorder_preserves_slots_and_pages_outside_filter(self):
        response = self.reorder([self.pages[2], self.pages[0]], "q=Sort")
        self.assertEqual(response.status_code, 302)
        for page in self.pages:
            page.refresh_from_db()
        self.assertEqual([page.order for page in self.pages], [30, 20, 10, 40])

    def test_reordering_second_page_does_not_move_it_before_first_page(self):
        with patch.object(PageAdmin, "list_per_page", 2):
            response = self.reorder([self.pages[3], self.pages[2]], "p=2")
        self.assertEqual(response.status_code, 302)
        for page in self.pages:
            page.refresh_from_db()
        self.assertEqual([page.order for page in self.pages], [10, 20, 40, 30])

    def test_invalid_reorder_is_rejected(self):
        data = {
            "_save": "Save",
            "form-TOTAL_FORMS": 2,
            "form-INITIAL_FORMS": 2,
            "form-0-uuid": self.pages[0].pk,
            "form-0-order": 0,
            "form-1-uuid": self.pages[1].pk,
            "form-1-order": 0,
        }
        response = self.client.post(self.url, data)
        self.assertContains(response, "Reload the page and reorder")
        self.pages[0].refresh_from_db()
        self.assertEqual(self.pages[0].order, 10)

    def test_equal_order_values_do_not_prevent_reordering(self):
        Page.objects.filter(pk__in=[self.pages[0].pk, self.pages[1].pk]).update(order=0)
        response = self.reorder([self.pages[1], self.pages[0]])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(Page.objects.filter(pk__in=[page.pk for page in self.pages]).values_list("pk", flat=True)),
            [self.pages[1].pk, self.pages[0].pk, self.pages[2].pk, self.pages[3].pk],
        )

    def test_equal_order_values_preserve_hidden_pages_relative_positions(self):
        Page.objects.filter(pk__in=[self.pages[0].pk, self.pages[1].pk]).update(order=0)
        response = self.reorder([self.pages[3], self.pages[0]])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(Page.objects.filter(pk__in=[page.pk for page in self.pages]).values_list("pk", flat=True)),
            [self.pages[3].pk, self.pages[1].pk, self.pages[2].pk, self.pages[0].pk],
        )

    def test_reorder_respects_admin_queryset(self):
        with patch.object(PageAdmin, "get_queryset", return_value=Page.objects.filter(pk=self.pages[0].pk)):
            self.reorder([self.pages[1], self.pages[0]])
        self.pages[1].refresh_from_db()
        self.assertEqual(self.pages[1].order, 20)

    def test_staff_without_change_permission_cannot_reorder(self):
        self.client.force_login(AdultFactory(_is_staff=True))
        response = self.reorder([self.pages[1], self.pages[0]])
        self.assertEqual(response.status_code, 403)

    def test_content_block_reorder_is_saved_for_current_parent_only(self):
        first = ContentBlock.objects.create(page=self.pages[0], heading="First", body="<p>First</p>", order=0)
        second = ContentBlock.objects.create(page=self.pages[0], heading="Second", body="<p>Second</p>", order=1)
        other = ContentBlock.objects.create(page=self.pages[1], body="<p>Other</p>", order=5)
        url = reverse("admin:pages_page_change", args=[self.pages[0].pk])
        response = self.client.get(url)
        self.assertContains(response, 'data-ordering-field="order"')
        data = {
            "title": self.pages[0].title,
            "slug": self.pages[0].slug,
            "content_blocks-TOTAL_FORMS": 2,
            "content_blocks-INITIAL_FORMS": 2,
            "_save": "Save",
        }
        for index, block in enumerate((first, second)):
            for name in ("uuid", "heading", "body", "visibility"):
                data[f"content_blocks-{index}-{name}"] = block.pk if name == "uuid" else getattr(block, name)
            data[f"content_blocks-{index}-order"] = 1 - index
            data[f"content_blocks-{index}-published_on_0"] = "2026-10-29"
            data[f"content_blocks-{index}-published_on_1"] = "12:00:00"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(self.pages[0].content_blocks.values_list("pk", flat=True)), [second.pk, first.pk])
        other.refresh_from_db()
        self.assertEqual(other.order, 5)

    def test_content_block_cannot_be_reassigned_by_inline_id(self):
        other = ContentBlock.objects.create(page=self.pages[1], body="<p>Other</p>", order=5)
        url = reverse("admin:pages_page_change", args=[self.pages[0].pk])
        response = self.client.post(
            url,
            {
                "title": self.pages[0].title,
                "slug": self.pages[0].slug,
                "content_blocks-TOTAL_FORMS": 1,
                "content_blocks-INITIAL_FORMS": 1,
                "content_blocks-0-uuid": other.pk,
                "content_blocks-0-body": "<p>Changed</p>",
                "content_blocks-0-visibility": "P",
                "content_blocks-0-order": 0,
                "_save": "Save",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        other.refresh_from_db()
        self.assertEqual(other.page_id, self.pages[1].pk)
        self.assertEqual(other.order, 5)
