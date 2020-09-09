from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

admin.site.login = login_required(admin.site.login)
admin.site.site_header = _('%(site)s Administration') % {'site': settings.PACK_NAME}
admin.site.site_title = _('%(site)s Admin') % {'site': settings.PACK_SHORTNAME}
admin.site.index_title = _('Pack Administration')
