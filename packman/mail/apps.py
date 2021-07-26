from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "packman.mail"
    verbose_name = _("Mail")
