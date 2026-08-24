"""
Who holds a Pack leadership title — Akela, Assistant Akela or Den Leader.

Lives here rather than with any one consumer because both the PWA's directory
and the main site's PackMate promotion ask the same question of the same
CommitteeMember rows.
"""

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


def is_pack_leader(user):
    """
    True when the signed-in user is an Akela, Assistant Akela or Den Leader.

    Fails closed and never raises: this is asked on every page render, so a
    Pack Year that can't be pinned down must cost us a promo banner rather than
    the whole site. PackYear.objects.current() does a bare .get() against a
    date range, which blows up both when no year covers today (rows are made
    lazily) and when two overlap (nothing stops the admin entering them).
    """
    # Scouts and anonymous visitors never carry committee assignments.
    if not getattr(user, "is_authenticated", False) or not hasattr(user, "committee_memberships"):
        return False
    try:
        return leadership_title(user) is not None
    except PackYear.DoesNotExist, PackYear.MultipleObjectsReturned:
        return False
