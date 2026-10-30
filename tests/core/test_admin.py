from __future__ import annotations

import re
import tempfile
from http import HTTPStatus
from io import BytesIO
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin.sites import AdminSite, all_sites
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Model
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from easy_thumbnails.files import get_thumbnailer
from PIL import Image
from tinymce.models import HTMLField
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin
from unittest_parametrize import ParametrizedTestCase, param, parametrize

from packman.core.navigation import admin_navigation
from packman.membership.factories import AdultFactory

User = get_user_model()

each_model_admin = parametrize(
    "site,model,model_admin",
    [
        param(
            site,
            model,
            model_admin,
            id=f"{site.name}_{str(model_admin).replace('.', '_')}",
        )
        for site in all_sites
        for model, model_admin in site._registry.items()
    ],
)


class ModelAdminTests(ParametrizedTestCase, TestCase):
    user: User

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(email="admin@example.com", password="test")  # nosec B106

    def setUp(self):
        self.client.force_login(self.user)

    def make_url(self, site: AdminSite, model: type[Model], page: str) -> str:
        return reverse(f"{site.name}:{model._meta.app_label}_{model._meta.model_name}_{page}")

    @each_model_admin
    def test_changelist(self, site, model, model_admin):
        url = self.make_url(site, model, "changelist")
        response = self.client.get(url, {"q": "example.com"})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @each_model_admin
    def test_add(self, site, model, model_admin):
        url = self.make_url(site, model, "add")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (
                HTTPStatus.OK,
                HTTPStatus.FORBIDDEN,  # some admin classes blanket disallow "add"
            ),
        )

    @each_model_admin
    def test_uses_unfold(self, site, model, model_admin):
        self.assertIsInstance(model_admin, ModelAdmin)

    @each_model_admin
    def test_rich_text_widgets_are_preserved(self, site, model, model_admin):
        response = self.client.get(self.make_url(site, model, "add"))
        if response.status_code == HTTPStatus.FORBIDDEN:
            return
        form = response.context["adminform"].form
        for field in model._meta.fields:
            if isinstance(field, HTMLField) and field.name in form.fields:
                self.assertIsInstance(form.fields[field.name].widget, TinyMCE)
        for inline in response.context["inline_admin_formsets"]:
            form = inline.formset.empty_form
            for field in inline.opts.model._meta.fields:
                if isinstance(field, HTMLField) and field.name in form.fields:
                    self.assertIsInstance(form.fields[field.name].widget, TinyMCE)


class AdminRedirectTests(TestCase):
    def test_canonical_urls(self):
        self.assertEqual(reverse("admin:index"), "/admin/")
        self.assertEqual(reverse("admin_system_info"), "/admin/system-info/")

    def test_legacy_bookmarks_preserve_paths_and_queries(self):
        for suffix in ("", "/", "/campaigns/order/?q=Jane&paid=false", "/doc/", "/system-info/"):
            with self.subTest(suffix=suffix):
                response = self.client.get(f"/administration{suffix}")
                self.assertEqual(response.status_code, HTTPStatus.PERMANENT_REDIRECT)
                self.assertEqual(response["Location"], f"/admin/{suffix.lstrip('/')}")

    def test_legacy_post_preserves_method(self):
        response = self.client.post("/administration/mail/message/add/", {"subject": "Draft"})
        self.assertEqual(response.status_code, HTTPStatus.PERMANENT_REDIRECT)
        self.assertEqual(response["Location"], "/admin/mail/message/add/")

    def test_legacy_redirect_rejects_unsafe_paths(self):
        for path in (
            "//outside.example/",
            "/%5C%5Coutside.example/",
            "/../outside/",
            "/%2e%2e/outside/",
            "/campaigns/../../outside/",
            "/campaigns/./order/",
        ):
            with self.subTest(path=path):
                with self.assertLogs("django.security.SuspiciousOperation", level="ERROR"):
                    response = self.client.get(f"/administration{path}")
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_legacy_redirect_escapes_path_delimiters(self):
        response = self.client.get("/administration/pages/page/a%3Fb%23c/change/?next=%2F%2Foutside.example")
        self.assertEqual(response.status_code, HTTPStatus.PERMANENT_REDIRECT)
        self.assertEqual(
            response["Location"],
            "/admin/pages/page/a%3Fb%23c/change/?next=%2F%2Foutside.example",
        )


class ChangelistGuidanceTests(TestCase):
    guidance_pages = (
        ("campaigns_campaign", "Starting a new campaign?"),
        ("campaigns_prizepoint", "Prize Points define"),
        ("compliance_requirement", "A Requirement is something"),
        ("compliance_requirementrecord", "A record is one Cub"),
    )

    def setUp(self):
        self.user = AdultFactory(_is_staff=True, is_superuser=True)
        self.client.force_login(self.user)

    def test_guidance_follows_add_in_a_cleared_content_toolbar(self):
        for model, guidance in self.guidance_pages:
            with self.subTest(model=model):
                response = self.client.get(reverse(f"admin:{model}_changelist"))
                add_url = reverse(f"admin:{model}_add")
                self.assertContains(response, guidance, count=1)
                self.assertContains(response, '<div id="changelist-guidance" style="clear: both;">', count=1)
                html = response.content.decode()
                content = html[html.index('id="content"') :]
                toolbar = content[: content.index('id="changelist-guidance"')]
                self.assertEqual(toolbar.count(f'href="{add_url}"'), 1)

    def test_guidance_remains_available_without_add_permission(self):
        self.user.is_superuser = False
        self.user.save()
        self.user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["view_campaign", "view_prizepoint", "view_requirement", "view_requirementrecord"]
            )
        )
        for model, guidance in self.guidance_pages:
            with self.subTest(model=model):
                response = self.client.get(reverse(f"admin:{model}_changelist"))
                self.assertContains(response, guidance, count=1)
                self.assertNotContains(response, f'href="{reverse(f"admin:{model}_add")}"')

    def test_popup_changelists_do_not_show_guidance(self):
        for model, guidance in self.guidance_pages:
            with self.subTest(model=model):
                response = self.client.get(reverse(f"admin:{model}_changelist"), {"_popup": "1"})
                self.assertNotContains(response, guidance)
                self.assertNotContains(response, 'id="changelist-guidance"')


class AdminNavigationTests(TestCase):
    @staticmethod
    def _leaf_items(items):
        return [child for item in items for child in item.get("items", [item])]

    def setUp(self):
        self.user = AdultFactory(_is_staff=True)
        self.client.force_login(self.user)

    def test_sidebar_respects_permissions(self):
        response = self.client.get(reverse("admin:index"))
        groups = admin_navigation(response.wsgi_request)
        self.assertEqual([str(group["title"]) for group in groups], ["System"])
        self.user.user_permissions.add(Permission.objects.get(codename="view_order"))
        response = self.client.get(reverse("admin:index"))
        groups = admin_navigation(response.wsgi_request)
        links = [item["link"] for group in groups for item in group["items"]]
        self.assertIn(reverse("admin:campaigns_order_changelist"), links)
        self.assertNotIn(reverse("admin:membership_adult_changelist"), links)

    def test_superuser_groups_and_all_models_remain_reachable(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "unfold/css/styles.css")
        groups = admin_navigation(response.wsgi_request)
        self.assertEqual(
            [str(group["title"]) for group in groups],
            ["Membership", "Compliance", "Fundraising", "Mail", "Content", "Calendar", "System"],
        )
        links = {item["link"] for group in groups for item in self._leaf_items(group["items"])}
        for app in response.context["available_apps"]:
            for model in app["models"]:
                if model.get("admin_url"):
                    self.assertIn(model["admin_url"], links)

    def test_requested_sidebar_groups_and_order(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("admin:index"))
        groups = {str(group["title"]): group["items"] for group in admin_navigation(response.wsgi_request)}

        def links(group):
            return [item["link"] for item in self._leaf_items(groups[group])]

        self.assertEqual(
            links("Membership"),
            [
                reverse("admin:committees_committee_changelist"),
                reverse("admin:membership_member_changelist"),
                reverse("admin:membership_adult_changelist"),
                reverse("admin:membership_scout_changelist"),
                reverse("admin:membership_family_changelist"),
                reverse("admin:dens_den_changelist"),
                reverse("admin:dens_rank_changelist"),
            ],
        )
        self.assertEqual(
            links("Compliance"),
            [
                reverse("admin:compliance_requirement_changelist"),
                reverse("admin:compliance_requirementrecord_changelist"),
            ],
        )
        self.assertEqual(
            links("Mail"),
            [
                reverse("admin:mail_message_changelist"),
                reverse("admin:mail_distributionlist_changelist"),
                reverse("admin:mail_listsettings_changelist"),
            ],
        )
        self.assertEqual(str(groups["Mail"][-1]["title"]), "Mail Settings")
        self.assertEqual([item["icon"] for item in groups["Mail"]], ["mail", "mail", "settings"])
        self.assertEqual(
            links("Content"),
            [
                reverse("admin:pages_page_changelist"),
                reverse("admin:documents_document_changelist"),
                reverse("admin:documents_category_changelist"),
            ],
        )
        self.assertEqual(
            links("Calendar"),
            [
                reverse("admin:calendars_event_changelist"),
                reverse("admin:calendars_category_changelist"),
                reverse("admin:address_book_venue_changelist"),
                reverse("admin:address_book_category_changelist"),
                reverse("admin:calendars_packyear_changelist"),
            ],
        )
        self.assertIn(reverse("admin:campaigns_category_changelist"), links("Fundraising"))
        category_titles = {
            item["link"]: str(item["title"])
            for item in self._leaf_items(groups["Calendar"])
            if item["link"]
            in {
                reverse("admin:calendars_category_changelist"),
                reverse("admin:address_book_category_changelist"),
            }
        }
        self.assertEqual(
            category_titles,
            {
                reverse("admin:calendars_category_changelist"): "Event Categories",
                reverse("admin:address_book_category_changelist"): "Venue Categories",
            },
        )
        self.assertNotIn(reverse("admin:mail_listsettings_changelist"), links("System"))
        all_links = [item["link"] for items in groups.values() for item in self._leaf_items(items)]
        self.assertEqual(len(all_links), len(set(all_links)))

    def test_sidebar_subgroups_and_order(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("admin:index"))
        groups = {str(group["title"]): group["items"] for group in admin_navigation(response.wsgi_request)}
        self.assertEqual(
            [str(item["title"]) for item in groups["Calendar"]],
            ["Events", "Event Categories", "Address Book", "Pack years"],
        )
        self.assertEqual(
            [str(item["title"]) for item in groups["Fundraising"]],
            ["Campaigns", "Customers", "Orders", "Prize Points", "Prizes", "Products"],
        )
        self.assertEqual([str(item["title"]) for item in groups["Content"]], ["Pages", "Documents"])
        for group, title, models in (
            ("Calendar", "Address Book", ("address_book_venue", "address_book_category")),
            (
                "Fundraising",
                "Products",
                ("campaigns_product", "campaigns_productline", "campaigns_category", "campaigns_tag"),
            ),
            ("Content", "Documents", ("documents_document", "documents_category")),
        ):
            with self.subTest(group=group):
                submenu = next(item for item in groups[group] if str(item["title"]) == title)
                self.assertEqual(
                    [item["link"] for item in submenu["items"]],
                    [reverse(f"admin:{model}_changelist") for model in models],
                )
                self.assertFalse(submenu["active"])
                self.assertEqual(submenu["link_attrs"]["role"], "button")
                self.assertEqual(submenu["link_attrs"]["tabindex"], "0")
                self.assertEqual(submenu["link_attrs"]["x-bind:aria-expanded"], "subnavigationOpen")

    def test_subgroups_only_show_permitted_children_and_expand_for_active_pages(self):
        for group, title, app_label, model_name in (
            ("Calendar", "Address Book", "address_book", "venue"),
            ("Calendar", "Address Book", "address_book", "category"),
            ("Fundraising", "Products", "campaigns", "product"),
            ("Fundraising", "Products", "campaigns", "productline"),
            ("Fundraising", "Products", "campaigns", "category"),
            ("Fundraising", "Products", "campaigns", "tag"),
            ("Content", "Documents", "documents", "document"),
            ("Content", "Documents", "documents", "category"),
        ):
            with self.subTest(model=f"{app_label}.{model_name}"):
                self.user.user_permissions.set(
                    Permission.objects.filter(
                        content_type__app_label=app_label,
                        content_type__model=model_name,
                        codename=f"view_{model_name}",
                    )
                )
                url = reverse(f"admin:{app_label}_{model_name}_changelist")
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                groups = {str(group["title"]): group["items"] for group in response.context["sidebar_navigation"]}
                self.assertEqual([str(item["title"]) for item in groups[group]], [title])
                submenu = groups[group][0]
                self.assertEqual([item["link"] for item in submenu["items"]], [url])
                self.assertTrue(submenu["active"])
                self.assertTrue(submenu["items"][0]["active"])
                self.assertContains(response, 'x-data="{navigationOpen: true}"')
                self.assertContains(response, "'subnavigationOpen': true")

                for suffix in ("add/", "1/change/", "1/history/"):
                    response.wsgi_request.path = f"{url}{suffix}"
                    navigation = admin.site.get_sidebar_list(response.wsgi_request)
                    active_group = next(item for item in navigation if str(item["title"]) == group)
                    self.assertTrue(active_group["items"][0]["active"])
                    self.assertTrue(active_group["items"][0]["items"][0]["active"])

    def test_empty_subgroups_are_omitted(self):
        self.user.user_permissions.set(
            Permission.objects.filter(
                codename__in=("view_event", "view_order", "view_page"),
                content_type__app_label__in=("calendars", "campaigns", "pages"),
            )
        )
        response = self.client.get(reverse("admin:index"))
        groups = admin_navigation(response.wsgi_request)
        self.assertFalse(any("items" in item for group in groups for item in group["items"]))

    def test_reordered_and_relocated_links_respect_permissions(self):
        for app_label, model_name in (
            ("membership", "scout"),
            ("compliance", "requirementrecord"),
            ("address_book", "category"),
            ("address_book", "venue"),
            ("mail", "listsettings"),
        ):
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                content_type__model=model_name,
                codename=f"view_{model_name}",
            )
            self.user.user_permissions.add(permission)

        response = self.client.get(reverse("admin:index"))
        groups = {str(group["title"]): group["items"] for group in admin_navigation(response.wsgi_request)}
        self.assertEqual(
            [item["link"] for item in groups["Membership"]], [reverse("admin:membership_scout_changelist")]
        )
        self.assertEqual(
            [item["link"] for item in groups["Compliance"]], [reverse("admin:compliance_requirementrecord_changelist")]
        )
        self.assertEqual(
            [item["link"] for item in self._leaf_items(groups["Calendar"])],
            [reverse("admin:address_book_venue_changelist"), reverse("admin:address_book_category_changelist")],
        )
        settings_url = reverse("admin:mail_listsettings_changelist")
        self.assertEqual([item["link"] for item in groups["Mail"]], [settings_url])
        self.assertNotIn(settings_url, [item["link"] for item in groups["System"]])

        response = self.client.get(settings_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mail = next(group for group in response.context["sidebar_navigation"] if str(group["title"]) == "Mail")
        self.assertTrue(mail["items"][0]["active"])
        self.assertContains(response, 'x-data="{navigationOpen: true}"')

    def test_system_info_requires_login_and_uses_theme(self):
        response = self.client.get(reverse("admin_system_info"))
        self.assertContains(response, "Installed Packages")
        self.assertContains(response, "unfold/css/styles.css")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("admin_system_info")).status_code, HTTPStatus.FOUND)

    def test_login_redirect_keeps_canonical_next_url(self):
        self.client.logout()
        response = self.client.get(reverse("admin:index"), follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("/admin/", response.wsgi_request.GET["next"])


class AdminAvatarTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings_override = override_settings(MEDIA_ROOT=media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.user = AdultFactory(_is_staff=True, first_name="Avatar", last_name="Tester")
        self.client.force_login(self.user)

    @staticmethod
    def photo_upload(name, color):
        buffer = BytesIO()
        Image.new("RGB", (200, 200), color).save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def avatar_markup(self, response):
        markup = render_to_string("unfold/helpers/avatar.html", {"user": response.wsgi_request.user})
        self.assertIn(markup.strip(), response.content.decode())
        return markup

    def assert_initial_avatar(self, response):
        markup = self.avatar_markup(response)
        self.assertNotIn("background-image:", markup)
        initial = re.escape(self.user.get_full_name()[0].upper())
        self.assertRegex(markup, rf">\s*{initial}\s*</div>")

    def test_signed_in_adults_photo_is_rendered_as_a_thumbnail(self):
        self.user.photo = self.photo_upload("own-photo.png", "navy")
        self.user.save()
        other = AdultFactory(_is_staff=True, photo=self.photo_upload("other-photo.png", "red"))

        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        avatar_url = response.wsgi_request.user.avatar_url
        self.assertIsNotNone(avatar_url)
        markup = self.avatar_markup(response)
        self.assertIn(f"background-image: url('{avatar_url}');", markup)
        self.assertNotIn(other.photo.name, markup)

        thumbnail = get_thumbnailer(self.user.photo).get_thumbnail({"size": (80, 80), "crop": "smart"})
        with Image.open(thumbnail.path) as image:
            self.assertEqual(image.size, (80, 80))
        self.assertEqual(avatar_url, thumbnail.url)

    def test_initial_is_shown_when_no_photo_exists(self):
        response = self.client.get(reverse("admin:index"))
        self.assertIsNone(response.wsgi_request.user.avatar_url)
        self.assert_initial_avatar(response)

    def test_missing_photo_falls_back_to_initial_and_logs_a_warning(self):
        self.user.photo = "headshots/missing/photo.png"
        self.user.save(update_fields=["photo"])

        with self.assertLogs("packman.membership.models", level="WARNING") as logs:
            response = self.client.get(reverse("admin:index"))
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assert_initial_avatar(response)

        self.assertTrue(all(self.user.photo.name not in message for message in logs.output))

    def test_unreadable_photo_falls_back_to_initial_and_logs_a_warning(self):
        self.user.photo = SimpleUploadedFile("broken.png", b"not an image", content_type="image/png")
        self.user.save()

        with self.assertLogs("packman.membership.models", level="WARNING"):
            response = self.client.get(reverse("admin:index"))
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assert_initial_avatar(response)

    def test_missing_thumbnail_falls_back_to_initial_and_logs_a_warning(self):
        self.user.photo = "headshots/example/photo.png"
        self.user.save(update_fields=["photo"])

        with patch("packman.membership.models.get_thumbnailer") as thumbnailer:
            thumbnailer.return_value.get_thumbnail.return_value = None
            with self.assertLogs("packman.membership.models", level="WARNING"):
                response = self.client.get(reverse("admin:index"))
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assert_initial_avatar(response)

    def test_unexpected_thumbnail_failures_are_not_swallowed(self):
        self.user.photo = "headshots/example/photo.png"
        with patch("packman.membership.models.get_thumbnailer", side_effect=RuntimeError("unexpected failure")):
            with self.assertRaisesRegex(RuntimeError, "unexpected failure"):
                self.user.avatar_url
