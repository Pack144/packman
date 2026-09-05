"""
Who holds a Pack leadership title — Akela, Assistant Akela or Den Leader.

Lives here rather than with any one consumer because both the PWA's directory
and the main site's PackMate promotion ask the same question of the same
CommitteeMember rows.
"""

from django.db.models import Q

from packman.calendars.models import PackYear
from packman.committees.models import CommitteeMember

# The three Pack leadership titles, most senior first — dict order is the
# precedence used when someone holds more than one (an Akela who also leads a
# den reads as "Akela"). Position's own numbering can't stand in for this:
# ASSISTANT_AKELA is 6, above AKELA's 5.
LEADERSHIP_TITLES = {
    CommitteeMember.Position.AKELA: CommitteeMember.Position.AKELA.label,
    CommitteeMember.Position.ASSISTANT_AKELA: CommitteeMember.Position.ASSISTANT_AKELA.label,
    CommitteeMember.Position.DEN_LEADER: CommitteeMember.Position.DEN_LEADER.label,
}


def assignment_title(assignment):
    """
    'Akela', 'Assistant Akela' or 'Den Leader' for one CommitteeMember, else None.

    Prefers the explicit position. Falls back to the committee's name, because a
    Pack may record the title there instead — committees flagged as Pack
    Leadership and named 'Assistant Akelas' or 'Den Leaders', whose members all
    sit at the default 'Member' position. Those names are plural while the
    position labels are singular, hence the removesuffix().
    """
    if assignment.position in LEADERSHIP_TITLES:
        return LEADERSHIP_TITLES[assignment.position]
    if not assignment.committee.leadership:
        return None
    name = assignment.committee.name.strip().removesuffix("s").casefold()
    return next((title for title in LEADERSHIP_TITLES.values() if title.casefold() == name), None)


def leadership_q(year, prefix="committee_membership__"):
    """
    Adults carrying a Pack leadership title in ``year``, as a Q against Adult.

    The queryset twin of assignment_title(), and it mirrors both of that
    function's paths: the explicit position, and the fallback to a committee
    flagged as Pack Leadership and named for the title. It lives beside that
    function so the two cannot drift apart.

    Every term belongs to a single filter() so that they all have to hold of
    the same assignment. Split across chained filters, an adult who led a den
    one year and sat on the popcorn committee the next would read as
    leadership in both.
    """
    # Committee names are plural where the position labels are singular, the
    # same allowance assignment_title() makes with removesuffix("s").
    named = Q(**{f"{prefix}committee__leadership": True})
    titles = Q()
    for title in LEADERSHIP_TITLES.values():
        titles |= Q(**{f"{prefix}committee__name__iexact": title})
        titles |= Q(**{f"{prefix}committee__name__iexact": f"{title}s"})

    return Q(**{f"{prefix}year": year}) & (Q(**{f"{prefix}position__in": list(LEADERSHIP_TITLES)}) | (named & titles))


def leadership_title(adult):
    """The Pack leadership title an Adult carries this Pack Year, or None."""
    titles = {
        title
        for assignment in adult.committee_memberships.filter(year=PackYear.objects.current()).select_related(
            "committee"
        )
        if (title := assignment_title(assignment))
    }
    return next((title for title in LEADERSHIP_TITLES.values() if title in titles), None)


def leads_or_serves_on(user, committees=()):
    """
    True when the user carries a Pack leadership title this Pack Year, or sits
    on one of the named committees.

    Committees are matched on slug or name, case-insensitively. The admin
    prepopulates the slug from the name but leaves both editable, so neither on
    its own is a dependable handle on a committee a Pack set up years ago.

    Fails closed and never raises: this is asked on every page render, so a
    Pack Year that can't be pinned down must cost us a promo banner rather than
    the whole site. PackYear.objects.current() does a bare .get() against a
    date range, which blows up both when no year covers today (rows are made
    lazily) and when two overlap (nothing stops the admin entering them).
    """
    # Scouts and anonymous visitors never carry committee assignments.
    if not getattr(user, "is_authenticated", False) or not hasattr(user, "committee_memberships"):
        return False

    wanted = {name.casefold() for name in committees}
    try:
        # One pass: the leadership title and the committee both come off the
        # same rows, and this runs on every page.
        assignments = user.committee_memberships.filter(year=PackYear.objects.current()).select_related("committee")
        return any(
            assignment_title(assignment)
            or assignment.committee.slug.casefold() in wanted
            or assignment.committee.name.strip().casefold() in wanted
            for assignment in assignments
        )
    except PackYear.DoesNotExist, PackYear.MultipleObjectsReturned:
        return False
