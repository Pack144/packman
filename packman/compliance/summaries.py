"""
Shared read models for a family's requirements.

Lives outside views.py so the membership pages can present the same summary
without importing a view or duplicating the grouping.
"""

from dataclasses import dataclass

from django.db.models import Q

from packman.calendars.models import PackYear
from packman.membership.models import Family, Scout

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
    Which of a family's Cubs are active this year, in one query. A withdrawn or
    graduated sibling is not being asked to renew.
    """
    return set(Scout.objects.active_in(year).filter(family=family).values_list("pk", flat=True))


def membership_standing(scout):
    """One Cub's registration as the family page shows it: a warn-ahead standing
    plus the ID and expiration date to sit alongside it."""
    return {
        "standing": standing_for(scout, warn_within=RENEWAL_WINDOW),
        "id": scout.scouting_membership_id,
        "expires_on": scout.scouting_membership_expires_on,
    }


def cub_group(scout, records, expected):
    """
    One Cub's group: their records plus the registration standing that sits
    above them.

    Module level rather than a closure inside group_by_subject() because the
    den dashboard builds the same group for a Cub who has no family on file and
    therefore no family to group under.
    """
    membership = membership_standing(scout)
    return {
        "subject": scout,
        "records": records,
        "membership": membership,
        "expected": expected,
        "registration_due": expected and membership["standing"] != Standing.CURRENT,
    }


def group_by_subject(family, records, active_cub_ids=frozenset(), include_unexpected=True):
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

    `include_unexpected` is what allows that last part. A family looking at its
    own page should see everything on file for it, but the den dashboard passes
    False: there `active_cub_ids` is one den's roster, and a sibling in another
    den holding records is not something that den's leader should be shown.

    A group's `expected` says the pack is asking that Cub for a registration;
    `registration_due` is the same but only while the standing is not current.
    Both the badge and the attention count read these, so they cannot tell the
    family different things.
    """
    by_member = {}
    household = []
    for record in records:
        if record.member_id:
            by_member.setdefault(record.member_id, []).append(record)
        else:
            household.append(record)

    groups = [
        cub_group(scout, by_member.get(scout.pk, []), expected=scout.pk in active_cub_ids)
        for scout in family.children.all()
        if scout.pk in active_cub_ids or (include_unexpected and by_member.get(scout.pk))
    ]
    groups += [
        {
            "subject": adult,
            "records": by_member.get(adult.pk, []),
            "membership": None,
            "expected": False,
            "registration_due": False,
        }
        for adult in family.adults.all()
    ]
    if household:
        groups.append(
            {"subject": family, "records": household, "membership": None, "expected": False, "registration_due": False}
        )
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


def count_needs_attention(family_id, year):
    """
    How many open items a family has: requirement records nobody has recorded,
    plus active Cubs whose registration is not current.

    Takes family_id rather than a Family so the home page banner stays cheap.
    summarize_family() answers the same question for a page that needs the
    detail behind it; the two read the same two sources, so they agree.
    """
    outstanding = RequirementRecord.objects.for_family(family_id).for_year(year).outstanding().count()
    due = sum(
        1
        for cub in Scout.objects.active_in(year).filter(family_id=family_id)
        if standing_for(cub, warn_within=RENEWAL_WINDOW) != Standing.CURRENT
    )
    return outstanding + due


@dataclass(frozen=True)
class RequirementStanding:
    """
    One requirement's standing across a den, shaped for
    compliance/snippets/requirement_progress.html.

    The pack dashboard gets the same four numbers from an annotated queryset
    (RequirementRollupMixin). A den is small enough that its records are
    already in memory by the time this is wanted, and tallying them there
    rather than issuing a second, den-joined aggregate keeps the bars and the
    rows underneath them counting exactly the same records.
    """

    name: str
    slug: str
    total: int
    complete: int
    waived: int
    outstanding: int


def _tally(groups):
    """The requirement standings and the open-item count for a set of groups."""
    counts = {}
    order = []
    open_items = 0
    for group in groups:
        for record in group["records"]:
            requirement = record.requirement
            if requirement.pk not in counts:
                counts[requirement.pk] = {"requirement": requirement, "total": 0, "complete": 0, "waived": 0}
                order.append(requirement.pk)
            tally = counts[requirement.pk]
            tally["total"] += 1
            if record.status == RequirementRecord.Status.COMPLETE:
                tally["complete"] += 1
            elif record.status == RequirementRecord.Status.WAIVED:
                tally["waived"] += 1
            if not record.is_satisfied:
                open_items += 1
        if group["registration_due"]:
            open_items += 1

    standings = [
        RequirementStanding(
            name=counts[pk]["requirement"].name,
            slug=counts[pk]["requirement"].slug,
            total=counts[pk]["total"],
            complete=counts[pk]["complete"],
            waived=counts[pk]["waived"],
            outstanding=counts[pk]["total"] - counts[pk]["complete"] - counts[pk]["waived"],
        )
        for pk in order
    ]
    return standings, open_items


def summarize_den(den, year):
    """
    Every household with a Cub in one den, for one pack year.

    What a den leader is shown: the Cubs assigned to *this* den, every adult in
    those Cubs' families, and the household's own requirements. A sibling in
    another den is left out even though the records hang off the same family --
    that Cub is another leader's to chase.

    Constant in queries regardless of den size: one for the roster, one for the
    records, and three for the families (Family's default manager already
    prefetches adults and children, which is what lets group_by_subject walk
    them without a query apiece).
    """
    cubs = Scout.objects.in_den(den, year)
    roster = list(cubs.select_related("family").order_by("last_name", "first_name"))

    cub_ids_by_family = {}
    # A Cub with no family on file still belongs on their den's page; their
    # records hang off the member alone, since save() has no family to
    # denormalize.
    unattached = []
    for cub in roster:
        if cub.family_id:
            cub_ids_by_family.setdefault(cub.family_id, set()).add(cub.pk)
        else:
            unattached.append(cub)

    records_by_family, records_by_cub = _den_records(year, cub_ids_by_family, unattached)

    rows = []
    families = Family.objects.filter(pk__in=cub_ids_by_family).order_by("name") if cub_ids_by_family else []
    for family in families:
        rows.append(
            _den_row(
                family,
                group_by_subject(
                    family,
                    records_by_family.get(family.pk, []),
                    cub_ids_by_family[family.pk],
                    include_unexpected=False,
                ),
            )
        )
    rows += [
        _den_row(None, [cub_group(cub, records_by_cub.get(cub.pk, []), expected=True)], label=str(cub))
        for cub in unattached
    ]

    requirements, outstanding = _tally(group for row in rows for group in row["groups"])
    return {
        "den": den,
        "cubs": cubs,
        "rows": rows,
        "requirements": requirements,
        "outstanding": outstanding,
        "total": len(rows),
        "settled": sum(1 for row in rows if not row["needs_attention"]),
        "year": year,
    }


def _den_records(year, cub_ids_by_family, unattached):
    """Every record the den's page will need, in one query, bucketed two ways."""
    by_family = {}
    by_cub = {}
    if not cub_ids_by_family and not unattached:
        return by_family, by_cub

    records = (
        RequirementRecord.objects.filter(year=year)
        .filter(Q(family_id__in=cub_ids_by_family) | Q(member_id__in=[cub.pk for cub in unattached]))
        .select_related("requirement", "member")
        .order_by("requirement__sort_order", "requirement__name")
    )
    for record in records:
        if record.family_id:
            by_family.setdefault(record.family_id, []).append(record)
        else:
            by_cub.setdefault(record.member_id, []).append(record)
    return by_family, by_cub


def _den_row(family, groups, label=None):
    """One card on the den page, carrying its own open-item count."""
    _, needs_attention = _tally(groups)
    return {
        "family": family,
        "label": label or str(family),
        "groups": groups,
        "needs_attention": needs_attention,
    }
