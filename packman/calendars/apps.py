from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CalendarsConfig(AppConfig):
    name = 'packman.calendars'
    verbose_name = _('Calendar')
