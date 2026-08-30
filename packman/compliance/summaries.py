"""
Shared read models for a family's requirements.

Lives outside views.py so the membership pages can present the same summary
without importing a view or duplicating the grouping.
"""

from packman.calendars.models import PackYear

from .models import RequirementRecord


def records_for_family(family, year=None):
    return (
        RequirementRecord.objects.filter(family=family, year=year or PackYear.objects.current())
        .select_related("requirement", "member")
        .order_by("requirement__sort_order", "requirement__name")
    )


def group_by_subject(family, records):
    """
    One group per person, plus one for the household, so a parent can see at a
    glance who still owes what.

    Cubs come first because they are usually what a parent is looking for.
    """
    by_member = {}
    household = []
    for record in records:
        if record.member_id:
            by_member.setdefault(record.member_id, []).append(record)
        else:
            household.append(record)

    groups = [{"subject": scout, "records": by_member.get(scout.pk, [])} for scout in family.children.all()]
    groups += [{"subject": adult, "records": by_member.get(adult.pk, [])} for adult in family.adults.all()]
    if household:
        groups.append({"subject": family, "records": household})
    return groups


def summarize_family(family, year=None):
    """The groups and the subset still needing attention, for one pack year."""
    if family is None:
        return {"groups": [], "outstanding": [], "year": year}

    year = year or PackYear.objects.current()
    records = list(records_for_family(family, year))
    return {
        "groups": group_by_subject(family, records),
        "outstanding": [record for record in records if not record.is_satisfied],
        "year": year,
    }
