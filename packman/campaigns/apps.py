from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FundraisersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "packman.campaigns"
    verbose_name = _("Fundraising Campaigns")
