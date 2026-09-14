from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.template import RequestContext, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse

from packman.membership.factories import AdultFactory
from packman.pages.models import ContentBlock, Page


class InlineCmsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.template = Template('{% load pages_tags %}{% inline_cms "cms-home" %}')

    def render(self, user=None):
        request = self.factory.get("/")
        request.user = user or AnonymousUser()
        return self.template.render(RequestContext(request))

    def grant(self, user, codename):
        permission = Permission.objects.get(
            codename=codename,
            content_type=ContentType.objects.get_for_model(Page),
        )
        user.user_permissions.add(permission)

    def test_renders_visible_inline_content(self):
        page = Page.objects.create(
            title="Home content",
            slug="cms-home",
            nav_placement=Page.NavPlacement.INLINE_CMS,
        )
        ContentBlock.objects.create(
            page=page,
            heading="Welcome",
            body="<p>Pack news</p>",
            visibility=ContentBlock.Visibility.PUBLIC,
        )

        content = self.render()

        self.assertIn("Welcome", content)
        self.assertIn("<p>Pack news</p>", content)

    def test_missing_content_shows_public_fallback(self):
        content = self.render()

        self.assertIn("This content is currently unavailable", content)
        self.assertIn("IT committee", content)
        self.assertNotIn("Create this content", content)

    def test_invisible_content_shows_public_fallback(self):
        page = Page.objects.create(
            title="Home content",
            slug="cms-home",
            nav_placement=Page.NavPlacement.INLINE_CMS,
        )
        ContentBlock.objects.create(
            page=page,
            body="<p>Members only</p>",
            visibility=ContentBlock.Visibility.PRIVATE,
        )

        content = self.render()

        self.assertIn("This content is currently unavailable", content)
        self.assertNotIn("Members only", content)

    def test_editor_can_create_missing_content_from_placeholder(self):
        editor = AdultFactory()
        self.grant(editor, "add_page")

        content = self.render(editor)

        self.assertIn("Create this content", content)
        self.assertIn("slug=cms-home&amp;nav_placement=7", content)

    def test_editor_can_open_existing_content(self):
        editor = AdultFactory()
        self.grant(editor, "change_page")
        page = Page.objects.create(
            title="Home content",
            slug="cms-home",
            nav_placement=Page.NavPlacement.INLINE_CMS,
        )
        ContentBlock.objects.create(
            page=page,
            body="<p>Pack news</p>",
            visibility=ContentBlock.Visibility.PUBLIC,
        )

        content = self.render(editor)

        self.assertIn("Edit this content", content)
        self.assertIn(reverse("admin:pages_page_change", args=(page.pk,)), content)
