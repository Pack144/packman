import logging

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    from_email = forms.EmailField(label=_('Your E-mail Address'), required=True)
    subject = forms.CharField(label=_('Subject'), max_length=998, required=True)
    message = forms.CharField(label=_('Message'), widget=forms.Textarea, required=True)

    def send_mail(self):
        subject = f"[{settings.PACK_SHORTNAME}] {self.cleaned_data['subject']}"
        from_email = self.cleaned_data['from_email']
        message = f"We have received the following message from {from_email}:" \
                  f"\n\n{self.cleaned_data['message']}"

        logger.info(f'Sending email from {from_email} with subject {subject}')
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['webmaster@pack144.org'])
