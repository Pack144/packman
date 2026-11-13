from django.contrib import admin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def admin_navigation(request):
    address_book_models = ("address_book.venue", "address_book.category")
    product_models = ("campaigns.product", "campaigns.productline", "campaigns.category", "campaigns.tag")
    document_models = ("documents.document", "documents.category")
    subgroups = (
        (_("Address Book"), address_book_models),
        (_("Products"), product_models),
        (_("Documents"), document_models),
    )
    groups = [
        (
            _("Membership"),
            ("membership", "dens", "committees"),
            "groups",
            (
                "committees.committee",
                "membership.member",
                "membership.adult",
                "membership.scout",
                "membership.family",
                "dens.den",
                "dens.rank",
            ),
        ),
        (
            _("Compliance"),
            ("compliance",),
            "checklist",
            ("compliance.requirement", "compliance.requirementrecord"),
        ),
        (
            _("Fundraising"),
            ("campaigns",),
            "storefront",
            (
                "campaigns.campaign",
                "campaigns.customer",
                "campaigns.order",
                "campaigns.prizepoint",
                "campaigns.prize",
                *product_models,
            ),
        ),
        (_("Mail"), ("mail",), "mail", ("mail.message", "mail.distributionlist", "mail.listsettings")),
        (_("Content"), ("pages", "documents"), "article", ("pages.page", *document_models)),
        (
            _("Calendar"),
            ("calendars", "address_book"),
            "calendar_month",
            (
                "calendars.event",
                "calendars.category",
                *address_book_models,
                "calendars.packyear",
            ),
        ),
        (_("System"), (), "settings", ()),
    ]
    apps = admin.site.get_app_list(request)
    grouped_labels = {label for _, labels, _, _ in groups for label in labels}
    assigned_models = {model for _, _, _, ordered_models in groups for model in ordered_models}
    model_titles = {
        "address_book.category": _("Venue Categories"),
        "calendars.category": _("Event Categories"),
        "mail.listsettings": _("Mail Settings"),
    }
    model_icons = {"mail.listsettings": "settings"}
    navigation = []
    for title, labels, icon, ordered_models in groups:
        positions = {model: index for index, model in enumerate(ordered_models)}
        selected = [
            (model["model"]._meta.label_lower, model)
            for app in apps
            for model in app["models"]
            if model.get("admin_url")
            and (
                model["model"]._meta.label_lower in positions
                or (
                    model["model"]._meta.label_lower not in assigned_models
                    and (app["app_label"] in labels or (not labels and app["app_label"] not in grouped_labels))
                )
            )
        ]
        selected.sort(key=lambda item: positions.get(item[0], len(positions)))
        model_items = {
            model_label: {
                "title": model_titles.get(model_label, model["name"]),
                "link": model["admin_url"],
                "icon": model_icons.get(model_label, icon),
            }
            for model_label, model in selected
        }
        items = list(model_items.values())
        for subgroup_title, model_labels in subgroups:
            children = [item for model_label, item in model_items.items() if model_label in model_labels]
            if children:
                position = items.index(children[0])
                items = [item for item in items if item not in children]
                # Unfold requires a link and an active state on subgroup toggles to open the outer group.
                items.insert(
                    position,
                    {
                        "title": subgroup_title,
                        "link": children[0]["link"],
                        "icon": icon,
                        "link_attrs": {
                            "role": "button",
                            "tabindex": "0",
                            "x-bind:aria-expanded": "subnavigationOpen",
                            "x-on:keydown.enter.prevent": "subnavigationOpen = !subnavigationOpen",
                            "x-on:keydown.space.prevent": "subnavigationOpen = !subnavigationOpen",
                        },
                        "items": children,
                        "active": any(request.path.startswith(child["link"]) for child in children),
                    },
                )
        if not labels and admin.site.has_permission(request):
            items.append({"title": _("System Information"), "link": reverse("admin_system_info"), "icon": "info"})
        if items:
            navigation.append({"title": title, "collapsible": True, "items": items})
    return navigation
