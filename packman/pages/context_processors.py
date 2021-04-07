from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from .models import Page


def populate_navbar(request):
    navbar = {
        "navbar_links": [],
        "pack": {
            "name": settings.PACK_NAME,
            "shortname": settings.PACK_SHORTNAME,
            "location": settings.PACK_LOCATION,
            "tagline": settings.PACK_TAGLINE,
        },
        "site": get_current_site(request),
    }
    for page in Page.objects.get_visible_content(user=request.user).filter(
        include_in_nav=True
    ):
        if page.content_blocks.count():
            navbar["navbar_links"].append(page)
    return navbar
