from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CommitteesConfig(AppConfig):
    name = "packman.committees"
    verbose_name = _("Committee")
