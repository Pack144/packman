import logging

from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse

logger = logging.getLogger(__name__)


class ListEmailMessage(EmailMultiAlternatives):
    """
    A version of EmailMultiAlternatives customized for sending messages to
    an email list.
    """

    def __init__(
        self,
        subject="",
        body="",
        from_email=None,
        to=None,
        bcc=None,
        connection=None,
        attachments=None,
        headers=None,
        alternatives=None,
        cc=None,
        reply_to=None,
        settings=None,
    ):
        self.settings = settings
        if settings:
            site = Site.objects.get_current()
            from_email = from_email or self.settings.from_email
            subject = f"{self.settings.subject_prefix} {subject}".strip()
            headers = headers or {}
            headers["List-Id"] = f"<{self.settings.list_id}> {self.settings.name}".strip()
            headers["List-Unsubscribe"] = f"<https://{site.domain}{reverse('membership:my-family')}>"

        super().__init__(
            subject,
            body,
            from_email,
            to,
            bcc,
            connection,
            attachments,
            headers,
            alternatives,
            cc,
            reply_to,
        )
