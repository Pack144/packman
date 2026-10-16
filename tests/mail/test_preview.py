from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from packman.mail.models import Attachment, DistributionList, Message, MessageRecipient, Thread
from packman.mail.rendering import render_message
from packman.membership.factories import AdultFactory


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class MessagePreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = AdultFactory()
        cls.other = AdultFactory()
        cls.distro = DistributionList.objects.create(name="Example list")

    def setUp(self):
        self.client.force_login(self.author)
        self.url = reverse("mail:preview")
        self.data = {"subject": "An unsaved message", "body": "<p>First.</p>\n<p>Second.</p>"}

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("no-store", response["Cache-Control"])

    def test_post_only(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.author)
        self.assertEqual(client.post(self.url, self.data).status_code, 403)

    def test_invalid_input_returns_errors(self):
        for data, field in (({"subject": "Subject"}, "body"), ({"body": "<p>Body</p>"}, "subject")):
            with self.subTest(field=field):
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["errors"])
                self.assertIn("no-store", response["Cache-Control"])
        response = self.client.post(self.url, {**self.data, "subject": "x" * 151})
        self.assertEqual(response.status_code, 400)

    def test_preview_is_personalized_to_current_user_without_side_effects(self):
        before = [model.objects.count() for model in (Message, Thread, MessageRecipient, Attachment)]
        with patch("packman.mail.models.Message.send") as send:
            response = self.client.post(
                self.url,
                {
                    **self.data,
                    "author": self.other.pk,
                    "recipient": self.other.pk,
                    "attachments": SimpleUploadedFile("ignored.txt", b"Not saved"),
                },
            )
        self.assertEqual(response.status_code, 200)
        html = response.json()["html"]
        self.assertIn(self.author.email, html)
        self.assertNotIn(self.other.email, html)
        self.assertNotIn("visiting our website", html)
        self.assertNotIn("/mail/", html)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("An unsaved message", html)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertEqual(before, [model.objects.count() for model in (Message, Thread, MessageRecipient, Attachment)])
        send.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

    def test_preview_and_delivery_use_identical_body_and_shell(self):
        message = Message.objects.create(author=self.author, **self.data)
        MessageRecipient.objects.create(message=message, recipient=self.author)
        preview = self.client.post(self.url, self.data).json()["html"]
        _, expected = render_message(message, self.author, preview=True)
        self.assertEqual(preview, expected)
        outgoing = message._personalize_messages()[0]
        _, sent_html = render_message(message, self.author)
        self.assertEqual(outgoing.alternatives[0].content, sent_html)
        self.assertIn(message.body, preview)
        self.assertIn(message.body, sent_html)
        self.assertIn("visiting our website", sent_html)
        self.assertEqual(outgoing.to, [f"{self.author} <{self.author.email}>"])

    def test_preview_cannot_mutate_an_existing_message(self):
        message = Message.objects.create(author=self.other, subject="Private", body="<p>Private body</p>")
        response = self.client.post(self.url, {**self.data, "pk": message.pk})
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertEqual(message.subject, "Private")
        self.assertNotIn("Private body", response.json()["html"])

    def test_new_and_draft_composers_offer_isolated_preview(self):
        message = Message.objects.create(author=self.author, **self.data)
        for url in (reverse("mail:create"), reverse("mail:update", kwargs={"pk": message.pk})):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'id="message-preview-button"')
                self.assertContains(response, 'sandbox=""')
                self.assertContains(response, 'data-preview-width="mobile"')

    def composer_data(self):
        return {
            **self.data,
            "to_field-TOTAL_FORMS": "1",
            "to_field-INITIAL_FORMS": "0",
            "to_field-MIN_NUM_FORMS": "1",
            "to_field-MAX_NUM_FORMS": "1000",
            "to_field-0-delivery": Message.Delivery.TO,
            "to_field-0-distribution_list": self.distro.pk,
        }

    def test_save_and_send_still_preserve_body_distribution_and_attachments(self):
        for action in ("_save", "_send"):
            with self.subTest(action=action):
                response = self.client.post(
                    reverse("mail:create"),
                    {
                        **self.composer_data(),
                        action: "1",
                        "attachments": SimpleUploadedFile("message.txt", b"An attachment"),
                    },
                )
                self.assertEqual(response.status_code, 302)
                message = Message.objects.latest("date_added")
                self.assertEqual(message.body, self.data["body"])
                self.assertEqual(list(message.distribution_lists.all()), [self.distro])
                attachment = message.attachments.get()
                self.addCleanup(attachment.filename.delete, save=False)
                self.assertEqual(message.status, Message.Status.DRAFT if action == "_save" else Message.Status.QUEUED)
                self.assertEqual(len(mail.outbox), 0)

    def test_draft_update_still_saves_current_body(self):
        message = Message.objects.create(author=self.author, subject="Original", body="<p>Original</p>")
        response = self.client.post(
            reverse("mail:update", kwargs={"pk": message.pk}),
            {**self.composer_data(), "_save": "1"},
        )
        self.assertEqual(response.status_code, 302)
        message.refresh_from_db()
        self.assertEqual(message.body, self.data["body"])
        self.assertEqual(message.status, Message.Status.DRAFT)
