"""
Shared read models for a family's requirements.

Lives outside views.py so the membership pages can present the same summary
without importing a view or duplicating the grouping.
"""

from packman.calendars.models import PackYear
from packman.membership.models import Scout

from .models import RequirementRecord
from .scouting_membership import RENEWAL_WINDOW, Standing, standing_for


def records_for_family(family, year=None):
    return (
        RequirementRecord.objects.filter(family=family, year=year or PackYear.objects.current())
        .select_related("requirement", "member")
        .order_by("requirement__sort_order", "requirement__name")
    )


def active_cub_ids(family, year):
    """
    Which of a family's Cubs the pack expects to hold a registration this year.

    One query. A withdrawn or graduated sibling is not being asked to renew.
    """
    return set(Scout.objects.active_in(year).filter(family=family).values_list("pk", flat=True))


def membership_standing(scout, expected):
    """
    One Cub's Scouting America registration as the family page shows it: a
    warn-ahead standing plus the ID and expiration date to sit alongside.

    `expected` says whether the pack is asking this Cub for one, which decides
    whether nothing on file reads as "Required" or as "Not on file". It is
    passed in rather than worked out here so that it cannot disagree with
    registration_due: asking the Cub's own status looks equivalent but is not,
    because active_in() wants a den membership for the year as well. A Cub who
    is ACTIVE but not in a den this year would have been badged as owing a
    registration the page had already decided not to count, which is the same
    banner-contradicts-badge bug the count was added to close.
    """
    return {
        "standing": standing_for(scout, warn_within=RENEWAL_WINDOW),
        "id": scout.scouting_membership_id,
        "expires_on": scout.scouting_membership_expires_on,
        "expected": expected,
    }


def group_by_subject(family, records, active_cub_ids=frozenset()):
    """
    One group per person, plus one for the household, so a parent can see at a
    glance who still owes what.

    Cubs come first because they are usually what a parent is looking for. Only
    Cubs carry a registration standing: adults and the household hold None,
    because the pack tracks registrations for its Cubs and leaves the adults'
    to council.

    Only the Cubs in `active_cub_ids` are shown: a sibling who has graduated or
    withdrawn is not part of the pack this year and reads as clutter on their
    family's page. A Cub who left part way through still appears if the year
    holds records for them, so nothing already on file quietly disappears.

    `registration_due` marks the standings the family is being asked to act on,
    and again only for those Cubs. A Cub who has left is shown their standing
    as a statement of fact and owes nothing.
    """
    by_member = {}
    household = []
    for record in records:
        if record.member_id:
            by_member.setdefault(record.member_id, []).append(record)
        else:
            household.append(record)

    def cub_group(scout):
        # One definition of "the pack is asking this Cub", shared by the badge
        # and the count so the two cannot tell the family different things.
        expected = scout.pk in active_cub_ids
        membership = membership_standing(scout, expected)
        return {
            "subject": scout,
            "records": by_member.get(scout.pk, []),
            "membership": membership,
            "registration_due": expected and membership["standing"] != Standing.CURRENT,
        }

    groups = [
        cub_group(scout) for scout in family.children.all() if scout.pk in active_cub_ids or by_member.get(scout.pk)
    ]
    groups += [
        {
            "subject": adult,
            "records": by_member.get(adult.pk, []),
            "membership": None,
            "registration_due": False,
        }
        for adult in family.adults.all()
    ]
    if household:
        groups.append({"subject": family, "records": household, "membership": None, "registration_due": False})
    return groups


def summarize_family(family, year=None):
    """The groups and everything still needing attention, for one pack year."""
    if family is None:
        return {"groups": [], "outstanding": [], "registrations_due": [], "needs_attention": 0, "year": year}

    year = year or PackYear.objects.current()
    records = list(records_for_family(family, year))
    groups = group_by_subject(family, records, active_cub_ids(family, year))
    outstanding = [record for record in records if not record.is_satisfied]
    registrations_due = [group["subject"] for group in groups if group["registration_due"]]
    return {
        "groups": groups,
        "outstanding": outstanding,
        "registrations_due": registrations_due,
        # A Cub the pack is waiting on a registration for is as much an open
        # item as a requirement nobody has recorded, so the page cannot call
        # itself up to date while either is true.
        "needs_attention": len(outstanding) + len(registrations_due),
        "year": year,
    }
