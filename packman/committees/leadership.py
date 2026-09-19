"""
Who holds a Pack leadership title — Akela, Assistant Akela or Den Leader.

Lives here rather than with any one consumer because both the PWA's directory
and the main site's PackMate promotion ask the same question of the same
CommitteeMember rows.
"""

from packman.calendars.models import PackYear
from packman.committees.models import CommitteeMember
from packman.dens.models import Den

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
    except (PackYear.DoesNotExist, PackYear.MultipleObjectsReturned):
        return False


def led_dens(user, year):
    """
    The Dens an Adult leads in a given Pack Year, ordered by number.

    Keyed on the den assignment rather than on Position.DEN_LEADER: as
    assignment_title() explains, a pack may record the title through the
    committee's name and leave everyone at the default 'Member' position, and
    those rows still carry the den. An Akela who also carries a den is
    supporting that den, so they belong here too.
    """
    if not getattr(user, "is_authenticated", False):
        return Den.objects.none()
    return Den.objects.filter(leadership__member=user, leadership__year=year).distinct().order_by("number")


def leads_any_den(user):
    """
    True when the Adult leads a den in any Pack Year.

    Year-agnostic on purpose: this answers "may they open the den dashboard at
    all", and a leader looking back at the den they ran two years ago is asking
    a reasonable question. Which den's data they actually see is settled
    per-year by led_dens().

    Asked on every page render to build the navbar, so it stays a single
    exists() and never widens to a join on Den.
    """
    if not getattr(user, "is_authenticated", False) or not hasattr(user, "committee_memberships"):
        return False
    return user.committee_memberships.filter(den__isnull=False).exists()
