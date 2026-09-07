from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.translation import gettext as _

from packman.campaigns.models import Campaign
from packman.pages.models import Page

# CMS pages that get a permanent, pinned slot in the top nav instead of being
# grouped under "Pack Info". The link label comes from the page's own CMS
# title, so it stays in sync if that's ever edited. Order here controls their
# order among the pinned links.
PINNED_PAGE_SLUGS = ["trackers"]

# CMS pages that belong under the "About" dropdown instead of "Pack Info".
# Order here controls their order within the dropdown.
ABOUT_PAGE_SLUGS = ["membership-requirements", "discipline-policy"]

# Fixed nav labels for the About/History links, always the same as their
# Page.PAGE_CHOICES display label rather than whatever a given Page row's
# (admin-editable) title happens to be.
PAGE_LABELS = dict(Page.PAGE_CHOICES)


def _is_active(request, *, apps=None, url_names=None, slug=None):
    """Determine whether a nav entry corresponds to the current page."""
    match = request.resolver_match
    if match is None:
        return False
    if apps and any(app in match.app_names for app in apps):
        return True
    if url_names and match.url_name in url_names:
        return True
    if slug and match.app_name == "pages" and match.kwargs.get("slug") == slug:
        return True
    return False


def _link(label, url, active):
    return {"kind": "link", "label": label, "url": url, "active": active}


def _dropdown(nav_id, label, items, *, align_end=False):
    return {
        "kind": "dropdown",
        "id": nav_id,
        "label": label,
        "active": any(item["active"] for item in items),
        "items": items,
        "align_end": align_end,
    }


def _page_link(page_or_slug, request, label=None):
    slug = page_or_slug if isinstance(page_or_slug, str) else page_or_slug.slug
    label = label or str(page_or_slug)
    return _link(label, reverse("pages:detail", kwargs={"slug": slug}), _is_active(request, slug=slug))


def _build_ncc_items(request, fundraiser):
    items = [
        _link(
            _("Fundraiser"),
            reverse("campaigns:order_list"),
            _is_active(request, url_names=["order_list", "order_list_by_campaign"]),
        )
    ]
    if fundraiser.can_select_prizes:
        items.append(
            _link(
                _("Prize Selection"),
                reverse("campaigns:prize_selection"),
                _is_active(request, url_names=["prize_selection"]),
            )
        )
    items.append(
        _link(
            _("Leaderboard"),
            reverse("campaigns:order_leaderboard"),
            _is_active(request, url_names=["order_leaderboard"]),
        )
    )
    items.append(
        _link(_("Products"), reverse("campaigns:product_list"), _is_active(request, url_names=["product_list"]))
    )
    items.append(_page_link("nccinfo", request, label=_("Information")))
    if request.user.has_perm("campaigns.generate_order_report"):
        items.append(
            _link(
                _("Order Report"),
                reverse("campaigns:order_report"),
                _is_active(request, url_names=["order_report", "order_report_by_campaign"]),
            )
        )
    return items


def _build_pack_info_items(request, navbar_links):
    items = [_link(_("Documents"), reverse("documents:list"), _is_active(request, apps=["documents"]))]
    skip_slugs = set(PINNED_PAGE_SLUGS) | set(ABOUT_PAGE_SLUGS)
    for page in navbar_links:
        if page.slug not in skip_slugs:
            items.append(_page_link(page, request))
    return items


def _build_dashboards_items(request):
    items = []
    if request.user.is_staff:
        items.append(_link(_("Admin"), reverse("admin:index"), False))
    if request.user.has_perm("compliance.view_all_records"):
        items.append(
            _link(_("Requirements"), reverse("compliance:dashboard"), _is_active(request, apps=["compliance"]))
        )
    return items


def _build_about_items(request, navbar_links):
    items = [
        _link(PAGE_LABELS[Page.ABOUT], reverse("pages:about"), _is_active(request, url_names=["about"])),
        _link(PAGE_LABELS[Page.HISTORY], reverse("pages:history"), _is_active(request, url_names=["history"])),
    ]
    pages_by_slug = {page.slug: page for page in navbar_links}
    for slug in ABOUT_PAGE_SLUGS:
        page = pages_by_slug.get(slug)
        if page:
            items.append(_page_link(page, request))
    items.append(_link(_("Contact Us"), reverse("pages:contact"), _is_active(request, url_names=["contact"])))
    return items


def _build_authenticated_nav(request, navbar_links, fundraiser):
    items = []
    if fundraiser:
        items.append(_dropdown("navbarNccDropdown", "NCC", _build_ncc_items(request, fundraiser)))
    items.append(_link(_("Calendar"), reverse("calendars:list"), _is_active(request, apps=["calendars"])))
    items.append(
        _link(
            _("Members"),
            reverse("membership:scouts"),
            _is_active(request, apps=["membership", "committees"]),
        )
    )
    pages_by_slug = {page.slug: page for page in navbar_links}
    for slug in PINNED_PAGE_SLUGS:
        page = pages_by_slug.get(slug)
        if page:
            items.append(_page_link(page, request))
    items.append(_dropdown("navbarPackInfoDropdown", _("Pack Info"), _build_pack_info_items(request, navbar_links)))
    items.append(
        _dropdown(
            "navbarAboutDropdown",
            _("About"),
            _build_about_items(request, navbar_links),
            align_end=True,
        )
    )
    return items


def _build_anonymous_nav(request, navbar_links):
    items = [
        _link(PAGE_LABELS[Page.ABOUT], reverse("pages:about"), _is_active(request, url_names=["about"])),
        _link(PAGE_LABELS[Page.HISTORY], reverse("pages:history"), _is_active(request, url_names=["history"])),
    ]
    items.extend(_page_link(page, request) for page in navbar_links)
    items.append(_link(_("Contact Us"), reverse("pages:contact"), _is_active(request, url_names=["contact"])))
    return items


def populate_navbar(request):
    navbar_links = [
        page
        for page in Page.objects.get_visible_content(user=request.user).filter(include_in_nav=True)
        if page.content_blocks.count()
    ]
    navbar = {
        "pack": {
            "name": settings.PACK_NAME,
            "shortname": settings.PACK_SHORTNAME,
            "location": settings.PACK_LOCATION,
            "tagline": settings.PACK_TAGLINE,
        },
        "site": get_current_site(request),
        # Rendered separately from navbar_items, on the right side of the nav
        # next to the account menu, so it reads as an "admin area" rather
        # than just another content link.
        "navbar_admin_dropdown": None,
    }
    if request.user.is_authenticated:
        fundraiser = Campaign.objects.current()
        navbar["navbar_items"] = _build_authenticated_nav(request, navbar_links, fundraiser)
        dashboards_items = _build_dashboards_items(request)
        if dashboards_items:
            navbar["navbar_admin_dropdown"] = _dropdown(
                "navbarDashboardsDropdown", _("Dashboards"), dashboards_items, align_end=True
            )
    else:
        navbar["navbar_items"] = _build_anonymous_nav(request, navbar_links)
    return navbar
