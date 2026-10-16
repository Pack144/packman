from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string


def render_message(message, recipient, *, preview: bool = False) -> tuple[str, str]:
    context = {
        "site": Site.objects.get_current(),
        "message": message,
        "recipient": recipient,
        "protocol": "https" if settings.CSRF_COOKIE_SECURE else "http",
        "preview": preview,
    }
    return (
        render_to_string("mail/message_body.txt", context),
        render_to_string("mail/message_body.html", context),
    )
