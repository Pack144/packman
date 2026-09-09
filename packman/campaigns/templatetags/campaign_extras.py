from decimal import Decimal

from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.simple_tag
def quota_progress(scout, campaign):
    """
    Determine a scout's fundraising tier for the given campaign — den
    quota, then the pack's $1,000 bronze / $1,500 silver / $2,000 gold medal
    milestones — and describe it as a stacked progress bar.

    The bar's 100% mark is always the top of the scout's current tier, with
    each earlier, fully-completed tier rendered as its own solid-colored
    segment and the remainder of the current tier rendered in that tier's
    color at reduced opacity, so the bar is always entirely filled.

    Requires the scout to have had a den membership, with a quota
    configured for that den, during the campaign's pack year; raises
    `Membership.DoesNotExist` or `Quota.DoesNotExist` otherwise.

    Returns a dict with the `next_tier_label` text for the tier heading, a
    `progress_text` string describing the milestone just reached, and a
    `segments` list (each a `{"pct", "color"}` dict, optionally with
    `"opacity"`) ready to be looped over to render the stacked bar.
    """
    den = scout.den_memberships.get(year_assigned=campaign.year).den
    quota = den.quotas.get(campaign=campaign).target

    products_total = scout.orders.filter(campaign=campaign).products_total()["total"]
    donations_total = scout.orders.filter(campaign=campaign).donations_total()["total"]
    total = products_total + donations_total

    # Each tier's incentive milestone (in dollars), the color used to
    # represent it in the bar, the label for the tier heading, and the
    # celebratory text shown (left-justified, opposite the label) once the
    # *previous* tier has just been passed to reach this one. The scout's
    # den quota is itself the first tier.
    # TODO: don't hard code these incentive milestones.
    tiers = [
        {
            "name": "quota",
            "milestone": quota,
            "color": "var(--bs-primary)",
            "label": _("Quota: $%(quota)s") % {"quota": quota},
            "progress_text": _("Working on making Quota!"),
        },
        {
            "name": "bronze",
            "milestone": Decimal("1000"),
            "color": "#977547",
            "label": _("Bronze Medal: $1,000"),
            "progress_text": _("Quota Met!"),
        },
        {
            "name": "silver",
            "milestone": Decimal("1500"),
            "color": "#D6D6D6",
            "label": _("Silver Medal: $1,500"),
            "progress_text": _("Bronze Medal Earned!"),
        },
        {
            "name": "gold",
            "milestone": Decimal("2000"),
            "color": "#e9af4e",
            "label": _("Gold Medal: $2,000"),
            "progress_text": _("Silver Medal Earned!"),
        },
    ]

    # Walk the tiers in order, tracking each one's dollar range (floor to
    # ceiling), building up `segments` as we go. Milestones are assumed to
    # be monotonically increasing, so each tier's ceiling is simply its own
    # milestone. Segments start out holding a dollar `amount` rather than a
    # percentage, since the bar's 100% mark (and so the scaling factor)
    # isn't known until the current tier is found.
    floor = Decimal("0")
    segments = []
    next_tier_label = progress_text = full_scale = None
    current_tier = None
    for tier in tiers:
        ceiling = tier["milestone"]
        # Hitting a tier's ceiling exactly means that tier is fully earned,
        # so the scout should already read as being in the *next* tier (at
        # 0% into it) — including falling through to "beyond" if this is
        # the last tier.
        reached = total < ceiling
        if reached:
            current_tier = tier
            break
        # This tier has been fully earned.
        segments.append({"amount": ceiling - floor, "color": tier["color"]})
        floor = ceiling

    if current_tier is not None:
        next_tier_label = current_tier["label"]
        progress_text = current_tier["progress_text"]
        full_scale = ceiling
        earned_in_tier = max(total - floor, Decimal("0"))
        segments.append({"amount": earned_in_tier, "color": current_tier["color"]})
        remaining = ceiling - floor - earned_in_tier
        if remaining > 0:
            # Whatever's left in the current tier's range still counts
            # toward it, so paint it the same color at a lower opacity
            # rather than leaving a blank/neutral gap at the end of the
            # bar.
            segments.append({"amount": remaining, "color": current_tier["color"], "opacity": 0.35})
    else:
        # Total exceeds every tier's ceiling; the bar is entirely solid.
        next_tier_label = _("Golden Peanut Contender")
        progress_text = _("Gold Medal Earned!")
        full_scale = floor

    # Drop zero-width segments so we don't render empty divs: a tier can end
    # up with $0 earned when a boundary is crossed exactly on the dollar,
    # fully earning one tier with nothing yet counted toward the next.
    segments = [
        {
            **segment,
            "pct": round(float(segment.pop("amount")) / float(full_scale) * 100, 2),
        }
        for segment in segments
        if segment["amount"] > 0
    ]

    return {
        "next_tier_label": next_tier_label,
        "progress_text": progress_text,
        "segments": segments,
        "total": total,
        "products_total": products_total,
        "donations_total": donations_total,
    }
