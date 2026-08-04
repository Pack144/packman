from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MobileConfig(AppConfig):
    name = "packman.mobile"
    verbose_name = _("Pack Directory (Mobile)")
