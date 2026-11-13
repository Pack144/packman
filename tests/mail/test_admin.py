from smtplib import SMTPException
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from packman.mail.models import DistributionList, ListSettings, Message
from packman.membership.factories import AdultFactory


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class MessageAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = AdultFactory(_is_staff=True, is_superuser=True)
        cls.recipient = AdultFactory()
        cls.other = AdultFactory(_is_staff=True, is_superuser=True)
        cls.draft = Message.objects.create(author=cls.author, subject="Draft", body="<p>Old body</p>")
        cls.distribution = DistributionList.objects.create(name="Test list")
        ListSettings.objects.create(list_id="https://example.com/mail/")

    def setUp(self):
        cache.clear()
        self.client.force_login(self.author)
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.add_url = reverse("admin:mail_message_add")
        self.change_url = reverse("admin:mail_message_change", args=[self.draft.pk])

    def post_data(self, url, send=True, attachment=False):
        response = self.client.get(url)
        data = {"subject": "Updated subject", "body": "<p>Updated body</p>"}
        for inline in response.context["inline_admin_formsets"]:
            formset = inline.formset
            prefix = formset.prefix
            data[f"{prefix}-TOTAL_FORMS"] = formset.initial_form_count()
            data[f"{prefix}-INITIAL_FORMS"] = formset.initial_form_count()
            model = formset.model.__name__
            if model == "MessageRecipient":
                data.update(
                    {
                        f"{prefix}-TOTAL_FORMS": 1,
                        f"{prefix}-0-recipient": self.recipient.pk,
                        f"{prefix}-0-delivery": "to",
                    }
                )
            elif model == "MessageDistribution":
                data.update(
                    {
                        f"{prefix}-TOTAL_FORMS": 1,
                        f"{prefix}-0-distribution_list": self.distribution.pk,
                        f"{prefix}-0-delivery": "to",
                    }
                )
            elif model == "Attachment" and attachment:
                data.update(
                    {
                        f"{prefix}-TOTAL_FORMS": 1,
                        f"{prefix}-0-filename": SimpleUploadedFile("test.txt", b"An attachment"),
                    }
                )
        data["mail_message_save_and_send" if send else "_save"] = "1"
        return data

    def test_native_action_is_visible_on_new_and_draft_messages(self):
        for url in (self.add_url, self.change_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'name="mail_message_save_and_send"')
                self.assertContains(response, "Save and send")

    def test_new_and_existing_messages_save_all_inlines_before_send(self):
        original_send = Message.send
        observed = []

        def verify_and_send(message):
            self.assertEqual(message.subject, "Updated subject")
            self.assertEqual(message.body, "<p>Updated body</p>")
            self.assertTrue(message.recipients.filter(pk=self.recipient.pk).exists())
            self.assertTrue(message.distribution_lists.filter(pk=self.distribution.pk).exists())
            self.assertEqual(message.attachments.count(), 1)
            observed.append(message.pk)
            original_send(message)

        for url in (self.add_url, self.change_url):
            with self.subTest(url=url):
                data = self.post_data(url, attachment=True)
                with patch.object(Message, "send", verify_and_send):
                    response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302)
                message = Message.objects.get(pk=observed[-1])
                self.assertEqual(message.status, Message.Status.SENT)
                self.assertIsNotNone(message.date_sent)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(len(mail.outbox[0].attachments), 1)

    def test_normal_save_keeps_draft(self):
        data = self.post_data(self.change_url, send=False)
        with patch.object(Message, "send") as send:
            response = self.client.post(self.change_url, data)
        self.assertEqual(response.status_code, 302)
        send.assert_not_called()
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, Message.Status.DRAFT)
        self.assertIsNone(self.draft.date_sent)

    def test_invalid_form_or_inline_does_not_send(self):
        for invalid_inline in (False, True):
            data = self.post_data(self.change_url)
            if invalid_inline:
                data["message_recipients-0-delivery"] = "invalid"
            else:
                data["subject"] = ""
            with patch.object(Message, "send") as send:
                response = self.client.post(self.change_url, data)
            self.assertEqual(response.status_code, 200)
            send.assert_not_called()

    def test_other_authors_and_sent_messages_cannot_send(self):
        data = self.post_data(self.change_url)
        self.client.force_login(self.other)
        with patch.object(Message, "send") as send:
            self.assertEqual(self.client.post(self.change_url, data).status_code, 403)
        send.assert_not_called()
        self.client.force_login(self.author)
        self.draft.date_sent = timezone.now()
        self.draft.status = Message.Status.SENT
        self.draft.save()
        with patch.object(Message, "send") as send:
            self.assertEqual(self.client.post(self.change_url, data).status_code, 403)
        send.assert_not_called()
        response = self.client.get(self.change_url)
        self.assertNotContains(response, 'name="mail_message_save_and_send"')

    def test_send_failure_is_not_reported_as_success(self):
        data = self.post_data(self.change_url)
        with patch.object(Message, "send", side_effect=SMTPException("Test delivery failure")):
            with self.assertRaisesMessage(SMTPException, "Test delivery failure"):
                self.client.post(self.change_url, data)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, Message.Status.DRAFT)
        self.assertIsNone(self.draft.date_sent)
        self.assertFalse(
            any("success" in message.tags for message in get_messages(self.client.request().wsgi_request))
        )

    def test_staff_without_message_permission_cannot_send(self):
        data = self.post_data(self.change_url)
        self.client.force_login(AdultFactory(_is_staff=True))
        with patch.object(Message, "send") as send:
            self.assertEqual(self.client.post(self.change_url, data).status_code, 403)
        send.assert_not_called()
