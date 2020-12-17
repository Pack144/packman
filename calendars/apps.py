from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PackCalendarConfig(AppConfig):
    name = 'calendars'
    verbose_name = _('Calendar')
