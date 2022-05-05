"""
WSGI config for packman.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/
"""

import logging
import os

from django.core.wsgi import get_wsgi_application
from django.utils.translation import gettext_lazy as _

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packman.settings.production")

application = get_wsgi_application()
logger = logging.getLogger(__name__)

try:
    from django.core.management import call_command

    import uwsgidecorators

    @uwsgidecorators.timer(10)
    def send_emails(num):
        """Send queued emails every 10 seconds"""
        call_command("sendemails")

except ImportError:
    logger.info(_("Module uwsgidecorators not found. Timers are disabled."))
