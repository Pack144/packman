from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from .models import Order


def email_receipt(order):
    site = Site.objects.get_current()

    context = {"site": site, "message": self, "recipient": recipient}
    subject = "[%s] %s" % (distros_string, self.subject)
    plaintext = render_to_string("mail/message_body.txt", context)
    richtext = render_to_string("mail/message_body.html", context)
