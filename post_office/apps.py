from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _("Post Office")
