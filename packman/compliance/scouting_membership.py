"""
Whether the pack's active Cubs hold a current Scouting America registration.

Deliberately outside the Requirement/RequirementRecord machinery. Those track
paperwork someone marks off for a pack year, and nothing there lapses part way
through. A registration is not like that: it has a hard expiration date, and the
answer already lives on the Cub. There is nothing for leadership to record and
nothing to keep in step, so this asks the Cubs directly rather than opening a
record against each of them.

Cubs only. Registered adults -- Akelas, Assistant Akelas, Den Leaders -- hold a
registration too, but the pack does not administer those and does not track
them; council is the record of truth and a copy here would only go stale.

The rule is written once, in Python, over an already loaded queryset. A pack has
tens of Cubs, not thousands, and the dashboard already loads every family; one
spelling of the rule is worth more here than an aggregate that could drift from
it.
"""

import datetime

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import PackYear
from packman.membership.models import Scout

# How long before a registration lapses we start calling it "expiring soon", for
# callers that ask to be warned (the family page). The dashboard does not.
RENEWAL_WINDOW = datetime.timedelta(days=60)


class Standing(models.TextChoices):
    """What a Cub's registration reads as today."""

    CURRENT = "CURRENT", _("Registered")
    EXPIRING_SOON = "EXPIRING_SOON", _("Expiring soon")
    EXPIRED = "EXPIRED", _("Expired")
    MISSING = "MISSING", _("Not on file")


def standing_for(cub, as_of=None, warn_within=None):
    """
    One Cub's registration standing.

    Both fields are needed: an ID with no expiration date says nothing about
    whether the registration is still good, so it does not count as on file.
    The expiration date is the last day the registration is held, so a
    registration expiring today is still current.

    Pass ``warn_within`` (a ``timedelta``) to get ``EXPIRING_SOON`` back for a
    registration that is still good but lapses within that window. Left unset it
    is never returned, so callers that only care whether a registration is good
    today (the dashboard) are unaffected.
    """
    as_of = as_of or timezone.localdate()
    expires_on = cub.scouting_membership_expires_on

    if not cub.scouting_membership_id or expires_on is None:
        return Standing.MISSING
    if expires_on < as_of:
        return Standing.EXPIRED
    if warn_within is not None and expires_on <= as_of + warn_within:
        return Standing.EXPIRING_SOON
    return Standing.CURRENT


def summarize_active_cubs(year=None, as_of=None):
    """
    Every active Cub's registration standing for a pack year, plus the counts.

    One query. ``as_of`` is the day the expiration dates are judged against and
    defaults to today, so switching the dashboard to an earlier pack year asks
    "are the Cubs who were active then registered now", not "were they then".
    """
    year = year or PackYear.objects.current()
    as_of = as_of or timezone.localdate()

    rows = []
    counts = dict.fromkeys(Standing.values, 0)
    for cub in Scout.objects.active_in(year).select_related("family").order_by("last_name", "first_name"):
        standing = standing_for(cub, as_of)
        counts[standing] += 1
        rows.append({"cub": cub, "standing": standing})

    return {
        "rows": rows,
        "total": len(rows),
        "current": counts[Standing.CURRENT],
        "expired": counts[Standing.EXPIRED],
        "missing": counts[Standing.MISSING],
        # What leadership has to chase: on file and lapsed, or never recorded.
        "outstanding": counts[Standing.EXPIRED] + counts[Standing.MISSING],
    }
