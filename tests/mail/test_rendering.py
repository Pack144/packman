from django.template.loader import render_to_string
from django.test import TestCase

from packman.mail.models import Message
from packman.membership.factories import AdultFactory


class MessageRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = AdultFactory()

    def assert_body_unchanged(self, body):
        message = Message.objects.create(author=self.author, subject="Formatting", body=body)
        for template in (
            "mail/message_body.html",
            "mail/partials/message.html",
            "mail/message_confirm_delete.html",
        ):
            with self.subTest(template=template):
                rendered = render_to_string(template, {"message": message, "recipient": self.author})
                self.assertIn(body, rendered)
                self.assertNotIn("<p><p>", rendered)
                self.assertNotIn("</p><br>", rendered)

    def test_html_paragraphs_do_not_gain_extra_breaks(self):
        for separator in ("\n", "\n\n", "\r\n", ""):
            with self.subTest(separator=separator):
                self.assert_body_unchanged(f"<p>First paragraph.</p>{separator}<p>Second paragraph.</p>")

    def test_single_paragraph_is_not_wrapped_in_another_paragraph(self):
        self.assert_body_unchanged("<p>A single paragraph.</p>")

    def test_intentional_formatting_is_unchanged(self):
        self.assert_body_unchanged(
            '<p style="margin-bottom: 20px; color: red;">First &amp; second.<br>Next line.</p>\n'
            "<p>&nbsp;</p><h2>Heading</h2><ul><li>Item</li></ul>"
            '<table><tr><td>Cell</td></tr></table><a href="https://example.com">Link</a>'
        )
