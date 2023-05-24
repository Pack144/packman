from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from packman.calendars.factories import EventFactory
from packman.calendars.models import Event
from packman.membership.factories import AdultFactory, CompleteFamilyFactory
from packman.membership.models import Adult


class EventListViewTestCase(TestCase):
    def setUp(self) -> None:
        self.url = reverse("calendars:list")
        EventFactory.create_batch(5)

    def test_url_resolves(self):
        self.assertEqual(self.url, "/calendar/")

    def test_get_as_anonymous_user(self):
        login_url = f"{reverse('login')}?next={self.url}"
        response = self.client.get(self.url)

        self.assertRedirects(response, login_url)

    def test_get_as_active_member(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "calendars/event_list.html")
        self.assertEqual(len(response.context["events"]), 5)


class EventDetailViewTestCase(TestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.url = reverse("calendars:detail", kwargs={"pk": self.event.pk})

    def test_url_resolves(self):
        self.assertEqual(self.url, f"/calendar/{self.event.pk}/")

    def test_get_as_anonymous_user(self):
        login_url = f"{reverse('login')}?next={self.url}"
        response = self.client.get(self.url)

        self.assertRedirects(response, login_url)

    def test_get_as_active_member(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "calendars/event_detail.html")
        self.assertContains(response, self.event.name)


class EventUpdateViewTestCase(TestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.url = reverse("calendars:update", kwargs={"pk": self.event.pk})
        self.content_type = ContentType.objects.get_for_model(Event)
        self.permission = Permission.objects.get(
            codename="change_event",
            content_type=self.content_type,
        )

    def test_url_resolves(self):
        self.assertEqual(self.url, f"/calendar/{self.event.pk}/edit/")

    def test_get_as_anonymous_user(self):
        login_url = f"{reverse('login')}?next={self.url}"
        response = self.client.get(self.url)

        self.assertRedirects(response, login_url)

    def test_get_as_standard_member_permission_denied(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_as_member_with_permission(self):
        member = AdultFactory(role=Adult.CONTRIBUTOR)
        member.user_permissions.add(self.permission)
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "calendars/event_form.html")
        self.assertContains(response, self.event.name)


class EventDeleteViewTestCase(TestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.url = reverse("calendars:delete", kwargs={"pk": self.event.pk})
        self.content_type = ContentType.objects.get_for_model(Event)
        self.permission = Permission.objects.get(
            codename="delete_event",
            content_type=self.content_type,
        )

    def test_url_resolves(self):
        self.assertEqual(self.url, f"/calendar/{self.event.pk}/delete/")

    def test_get_as_anonymous_user(self):
        login_url = f"{reverse('login')}?next={self.url}"
        response = self.client.get(self.url)

        self.assertRedirects(response, login_url)

    def test_get_as_standard_member_permission_denied(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_as_member_with_permission(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        member.user_permissions.add(self.permission)
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "calendars/event_confirm_delete.html")
        self.assertContains(response, self.event.name)


class EventCreateViewTestCase(TestCase):
    def setUp(self) -> None:
        self.url = reverse("calendars:create")
        self.content_type = ContentType.objects.get_for_model(Event)
        self.permission = Permission.objects.get(
            codename="add_event",
            content_type=self.content_type,
        )

    def test_url_resolves(self):
        self.assertEqual(self.url, "/calendar/add/")

    def test_get_as_anonymous_user(self):
        login_url = f"{reverse('login')}?next={self.url}"
        response = self.client.get(self.url)

        self.assertRedirects(response, login_url)

    def test_get_as_standard_member_permission_denied(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_as_member_with_permission(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        member.user_permissions.add(self.permission)
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "calendars/event_form.html")


class EventArchiveViewTestCase(TestCase):
    def setUp(self) -> None:
        self.url = reverse("calendars:archive")
        EventFactory.create_batch(5, future=False)

    def test_url_resolves(self):
        self.assertEqual(self.url, "/calendar/archive/")

    def test_get_as_anonymous_user(self):
        login_url = f"{reverse('login')}?next={self.url}"
        response = self.client.get(self.url)

        self.assertRedirects(response, login_url)

    def test_get_as_active_member(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "calendars/event_archive.html")
        self.assertEqual(len(response.context["events"]), 5)


class EventFeedTestCase(TestCase):
    def setUp(self) -> None:
        self.family = CompleteFamilyFactory(active_children=1)
        self.url = reverse("calendars:feed", args=(self.family.pk,))
        EventFactory.create_batch(25)

    def test_url_resolves(self):
        self.assertEqual(self.url, f"/calendar/feed/{self.family.pk}.ics")

    def test_get(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
