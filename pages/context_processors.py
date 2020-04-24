from django.conf import settings
from django.db.models import Q

from .models import DynamicPage, Content


def navbar_items(request):
    navbar = {
        'pack_name': settings.PACK_NAME,
        'pack_location': settings.PACK_LOCATION,
        'pack_tagline': settings.PACK_TAGLINE,
        'public_pages': [],
        'private_pages': [],
    }
    for page in DynamicPage.objects.filter(include_in_nav=True):
        if page.content_set.filter(Q(visibility=Content.PUBLIC) | Q(visibility=Content.ANONYMOUS)):
            navbar['public_pages'].append(page)
        else:
            navbar['private_pages'].append(page)

    return navbar
