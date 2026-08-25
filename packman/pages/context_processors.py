from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from packman.campaigns.models import Campaign
from packman.committees.leadership import leads_or_serves_on
from packman.membership.mixins import is_active_member_or_contributor
from packman.pages.models import Page

# Committees whose members are shown PackMate alongside the Pack's Akelas,
# Assistant Akelas and Den Leaders. Add a name or slug here to widen it.
PACKMATE_COMMITTEES = ("membership",)


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
        "fundraiser": Campaign.objects.current(),
        # PackMate is pitched to the people who run the Pack, and only where
        # the app would actually let them in.
        "packmate_available": is_active_member_or_contributor(request.user)
        and leads_or_serves_on(request.user, PACKMATE_COMMITTEES),
    }
    for page in Page.objects.get_visible_content(user=request.user).filter(include_in_nav=True):
        if page.content_blocks.count():
            navbar["navbar_links"].append(page)
    return navbar
