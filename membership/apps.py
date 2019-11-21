from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MembershipConfig(AppConfig):
    name = 'membership'
    verbose_name = _('Membership')

    def ready(self):
        import membership.signals
