import logging

from django import forms
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.translation import gettext as _

from tinymce.widgets import TinyMCE

from packman.core.exceptions import SpamDetected

from .models import ContentBlock, Page

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    from_name = forms.CharField(
        label=_("Your Name"),
        help_text=_("What is your name"),
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your Name"}),
        required=True,
    )
    from_email = forms.EmailField(
        label=_("Your E-mail"),
        help_text=_("How can we get a hold of you"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "email@example.com"}),
        required=True,
    )
    url = forms.URLField(
        # A fake field to catch spambots using the form. May also be read by screen readers.
        label=_("Webpage"),
        help_text=_("Optionally give us your website"),
        widget=forms.URLInput(attrs={"autocomplete": "off", "placeholder": "https://example.com"}),
        required=False,
    )
    subject = forms.CharField(
        label=_("Subject"),
        help_text=_("Briefly describe the reason you are contacting us"),
        max_length=998,
        widget=forms.TextInput(attrs={"placeholder": "Message subject"}),
        required=True,
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={"placeholder": "Your message"}),
        required=True,
    )

    def clean_url(self):
        url = self.cleaned_data.get("url")
        if url:
            raise SpamDetected(
                _(
                    "Invalid input detected on this form. If you believe you received this message "
                    "in error, please you may check your query and try again."
                )
            )

    def send_mail(self):
        from_address = f"{self.cleaned_data['from_name']} <{self.cleaned_data['from_email']}>"
        email = EmailMessage(
            subject=f"{settings.EMAIL_SUBJECT_PREFIX}{self.cleaned_data['subject']}",
            body=f"We have received the following message from {from_address}:\n\n{self.cleaned_data['message']}",
            to=[f"{a[0]} <{a[1]}>" for a in settings.MANAGERS],
            reply_to=[from_address],
        )
        logger.info(f"Sending email from {email.reply_to} with the subject '{email.subject}' to '{email.to}'")
        email.send()


class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = ("heading", "bookmark", "visibility", "body")
        widgets = {
            "body": TinyMCE(mce_attrs={"link_list": "api/v1/pages/link_list/"}),
            "visibility": forms.RadioSelect,
        }


ContentBlockFormSet = forms.inlineformset_factory(
    Page,
    ContentBlock,
    form=ContentBlockForm,
    can_delete=True,
    # can_order=True,
    extra=0,
    min_num=1,
)


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ("title", "slug", "include_in_nav")
