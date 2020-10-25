import logging

from django import forms
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    from_name = forms.CharField(
        label=_('Your Name'),
        max_length=254,
        widget=forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': 'Mary Smith'}),
        required=True,
    )
    from_email = forms.EmailField(
        label=_('Your E-mail'),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'email@example.com'}),
        required=True,
    )
    subject = forms.CharField(
        label=_('Subject'),
        max_length=998,
        widget=forms.TextInput(attrs={'placeholder': 'Message subject'}),
        required=True,
    )
    message = forms.CharField(
        label=_('Message'),
        widget=forms.Textarea(attrs={'placeholder': 'Your message'}),
        required=True
    )

    def send_mail(self):
        from_address = f"{self.cleaned_data['from_name']} <{self.cleaned_data['from_email']}>"
        email = EmailMessage(
            subject=f"{settings.EMAIL_SUBJECT_PREFIX}{self.cleaned_data['subject']}",
            body=f"We have received the following message from "
                 f"{from_address}:"
                 f"\n\n{self.cleaned_data['message']}",
            to=settings.MANAGERS,
            reply_to=[from_address],
        )
        logger.info(f"Sending email from {email.reply_to} with the subject '{email.subject}' to '{email.to}'")
        email.send()
