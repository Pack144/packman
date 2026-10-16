from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase

from packman.mail.forms import MessageForm
from packman.mail.models import Message
from packman.mail.rendering import EDITOR_STYLE, PARAGRAPH_STYLE, render_body
from packman.membership.factories import AdultFactory


class MessageRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = AdultFactory()

    def test_email_does_not_add_breaks_to_html_paragraphs(self):
        message = Message(author=self.author, subject="Paragraphs", body="<p>First.</p>\n<p>Second.</p>")
        rendered = render_to_string("mail/message_body.html", {"message": message, "recipient": self.author})
        self.assertNotIn("<p><p>", rendered)
        self.assertNotIn("</p><br>", rendered)
        self.assertIn('style="margin: 0 0 8px; line-height: 1.4;"', rendered)

    def test_website_uses_same_paragraph_defaults(self):
        message = Message.objects.create(author=self.author, subject="Paragraphs", body="<p>First.</p>")
        for template in ("mail/partials/message.html", "mail/message_confirm_delete.html"):
            with self.subTest(template=template):
                rendered = render_to_string(template, {"message": message})
                self.assertNotIn("<p><p>", rendered)
                self.assertIn('style="margin: 0 0 8px; line-height: 1.4;"', rendered)


class BodyRenderingTests(SimpleTestCase):
    def test_html_whitespace_does_not_become_breaks(self):
        for separator in ("\n", "\n\n", "\r\n", ""):
            with self.subTest(separator=separator):
                rendered = render_body(f"<p>First.</p>{separator}<p>Second.</p>")
                self.assertEqual(rendered.count("<p "), 2)
                self.assertNotIn("<br", rendered)
                self.assertEqual(rendered.count(PARAGRAPH_STYLE), 2)

    def test_preserves_explicit_formatting_and_rich_content(self):
        body = (
            '<p class="intro" style="margin-bottom: 20px; color: red;">First &amp; second.<br>Next.</p>\n'
            "<p>&nbsp;</p><h2>Heading</h2><ul><li>Item</li></ul>"
            '<table><tr><td>Cell</td></tr></table><a href="https://example.com">Link</a>'
            '<img src="/logo.png" alt="Logo">'
        )
        rendered = render_body(body)
        self.assertIn(f'style="{PARAGRAPH_STYLE} margin-bottom: 20px; color: red;"', rendered)
        self.assertIn('class="intro"', rendered)
        self.assertIn(f'<p style="{PARAGRAPH_STYLE}">&nbsp;</p>', rendered)
        self.assertIn("First &amp; second.<br>Next.", rendered)
        self.assertTrue(rendered.endswith(body[body.index("<h2>") :]))

    def test_legacy_plain_text_retains_paragraphs_and_line_breaks(self):
        self.assertEqual(
            render_body("First & second.\nNext line.\n\nAnother paragraph."),
            f'<p style="{PARAGRAPH_STYLE}">First &amp; second.<br>Next line.</p>\n\n'
            f'<p style="{PARAGRAPH_STYLE}">Another paragraph.</p>',
        )

    def test_empty_body(self):
        self.assertEqual(render_body(""), f'<p style="{PARAGRAPH_STYLE}"></p>')

    def test_comments_and_non_paragraph_tags_are_unchanged(self):
        body = '<!-- a comment --><div data-title="A &amp; B">Text<br /></div>'
        self.assertEqual(render_body(body), body)

    def test_multiline_start_tag_and_attributes(self):
        self.assertEqual(
            render_body('<div>One</div>\n<p\n title="A &amp; B">Two</p>'),
            f'<div>One</div>\n<p title="A &amp; B" style="{PARAGRAPH_STYLE}">Two</p>',
        )

    def test_mail_widget_has_matching_styles(self):
        self.assertEqual(MessageForm().fields["body"].widget.mce_attrs["content_style"], EDITOR_STYLE)
