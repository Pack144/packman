from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AddressBookConfig(AppConfig):
    name = "packman.address_book"
    verbose_name = _("Address Book")
