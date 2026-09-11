from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.translation import gettext as _

from packman.campaigns.models import Campaign
from packman.pages.models import Page


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


def _page_link(page, request, label=None):
    label = label or str(page)
    return _link(label, reverse("pages:detail", kwargs={"slug": page.slug}), _is_active(request, slug=page.slug))


def _group_navbar_links(navbar_links):
    """
    Split pages by their admin-editable nav_placement. navbar_links is
    already ordered (Page.Meta.ordering), so each group keeps that relative
    order.
    """
    groups = {placement: [] for placement in Page.NAV_GROUP_PLACEMENTS}
    for page in navbar_links:
        groups[page.nav_placement].append(page)
    return groups


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
            _is_active(
                request,
                url_names=["order_leaderboard", "order_leaderboard_by_campaign", "order_leaderboard_legacy"],
            ),
        )
    )
    items.append(
        _link(_("Products"), reverse("campaigns:product_list"), _is_active(request, url_names=["product_list"]))
    )
    ncc_pages = [
        page
        for page in Page.objects.get_visible_content(user=request.user).filter(nav_placement=Page.NavPlacement.NCC)
        if page.content_blocks.count()
    ]
    items.extend(_page_link(page, request) for page in ncc_pages)
    if request.user.has_perm("campaigns.generate_order_report"):
        items.append(
            _link(
                _("Order Report"),
                reverse("campaigns:order_report"),
                _is_active(request, url_names=["order_report", "order_report_by_campaign"]),
            )
        )
    return items


def _build_pack_info_items(request, pack_info_pages):
    items = [_link(_("Documents"), reverse("documents:list"), _is_active(request, apps=["documents"]))]
    items.extend(_page_link(page, request) for page in pack_info_pages)
    return items


def _build_dashboards_items(request):
    items = []
    if request.user.is_staff:
        items.append(_link(_("Site Admin"), reverse("admin:index"), False))
    if request.user.has_perm("compliance.view_all_records"):
        items.append(
            _link(
                _("Requirements Dashboard"), reverse("compliance:dashboard"), _is_active(request, apps=["compliance"])
            )
        )
    return items


def _build_about_items(request, about_pages):
    items = [_page_link(page, request) for page in about_pages]
    items.append(_link(_("Contact Us"), reverse("pages:contact"), _is_active(request, url_names=["contact"])))
    return items


def _build_authenticated_nav(request, navbar_links, fundraiser):
    navbar_groups = _group_navbar_links(navbar_links)
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
    items.extend(_page_link(page, request) for page in navbar_groups[Page.NavPlacement.PINNED])
    items.append(
        _dropdown(
            "navbarPackInfoDropdown",
            _("Pack Info"),
            _build_pack_info_items(request, navbar_groups[Page.NavPlacement.PACK_INFO]),
        )
    )
    items.append(
        _dropdown(
            "navbarAboutDropdown",
            _("About"),
            _build_about_items(request, navbar_groups[Page.NavPlacement.ABOUT]),
            align_end=True,
        )
    )
    return items


def _build_anonymous_nav(request, navbar_links):
    # Anonymous visitors don't see enough links to warrant grouping them into
    # dropdowns, so just show them all in whatever order they're already in.
    items = [_page_link(page, request) for page in navbar_links]
    items.append(_link(_("Contact Us"), reverse("pages:contact"), _is_active(request, url_names=["contact"])))
    return items


def populate_navbar(request):
    navbar_links = [
        page
        for page in Page.objects.get_visible_content(user=request.user).filter(
            nav_placement__in=Page.NAV_GROUP_PLACEMENTS
        )
        if page.content_blocks.count()
    ]

    navbar_admin_dropdown = None
    if request.user.is_authenticated:
        fundraiser = Campaign.objects.current()
        navbar_items = _build_authenticated_nav(request, navbar_links, fundraiser)
        dashboards_items = _build_dashboards_items(request)
        if dashboards_items:
            navbar_admin_dropdown = _dropdown("navbarDashboardsDropdown", _("Admin"), dashboards_items, align_end=True)
    else:
        navbar_items = _build_anonymous_nav(request, navbar_links)

    return {
        "pack": {
            "name": settings.PACK_NAME,
            "shortname": settings.PACK_SHORTNAME,
            "location": settings.PACK_LOCATION,
            "tagline": settings.PACK_TAGLINE,
        },
        "site": get_current_site(request),
        "navbar_items": navbar_items,
        # Rendered separately from navbar_items, on the right side of the nav
        # next to the account menu, so it reads as an "admin area" rather
        # than just another content link.
        "navbar_admin_dropdown": navbar_admin_dropdown,
    }
