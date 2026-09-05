"""
Requirements whose standing is read off the member rather than recorded by hand.

Most requirements are a status someone sets in the admin. A Scouting America
registration is not: it has a hard expiration date, and the truth already lives
on the Member. Deriving it means the report cannot claim a leader is registered
the morning after their membership lapsed.

The rule is spelled out twice here -- once in Python for a single record, once
as a Q for the dashboard's aggregate queries. Both live in this module so that a
change to one is made staring at the other. tests/compliance/test_managers.py
asserts the two agree.

The three derived states partition on the two fields, with no gap and no
overlap:

    no ID, or no expiration date on file  -> not started
    ID and an expiration date still ahead -> complete
    ID and an expiration date now past    -> expired
"""

from django.db.models import Q
from django.utils import timezone


def _as_of(as_of=None):
    return as_of or timezone.localdate()


def _on_file(member):
    return bool(member.scouting_membership_id) and member.scouting_membership_expires_on is not None


def scouting_membership_satisfied(member, as_of=None):
    """True when this member has a membership ID on file that has not expired."""
    if member is None or not _on_file(member):
        return False
    return member.scouting_membership_expires_on >= _as_of(as_of)


def scouting_membership_expired(member, as_of=None):
    """True when a membership was recorded and its expiration date has passed."""
    if member is None or not _on_file(member):
        return False
    return member.scouting_membership_expires_on < _as_of(as_of)


def scouting_membership_q(prefix="", as_of=None, expired=False):
    """
    The same tests as a Q, against whatever holds the Member fields.

    ``prefix`` is the lookup path to the member: "" from Member itself,
    "member__" from a RequirementRecord, "record__member__" from a Requirement.

    Member.save() strips the ID, so excluding "" here and testing truthiness in
    Python agree on what "on file" means.
    """
    on_file = ~Q(**{f"{prefix}scouting_membership_id": ""}) & Q(
        **{f"{prefix}scouting_membership_expires_on__isnull": False}
    )
    lookup = "__lt" if expired else "__gte"
    return on_file & Q(**{f"{prefix}scouting_membership_expires_on{lookup}": _as_of(as_of)})


def status_q(status, prefix="record__", source_prefix="", as_of=None):
    """
    Records sitting at ``status``, honouring how their requirement is sourced.

    Needed because the dashboard rollup annotates over Requirement, where the
    annotation from RequirementRecordQuerySet.with_effective_status() is not
    available. ``source_prefix`` is the path to the Requirement: "" when
    annotating over it, "requirement__" when grouping records.
    """
    from .models import Requirement, RequirementRecord

    Status = RequirementRecord.Status
    record_status = f"{prefix}status"

    manual = Q(**{f"{source_prefix}source": Requirement.Source.MANUAL})
    derived = Q(**{f"{source_prefix}source": Requirement.Source.SCOUTING_MEMBERSHIP})
    # Waiving is leadership excusing someone, so it outranks what either the
    # record or the member's own fields would otherwise say.
    waived = Q(**{record_status: Status.WAIVED})

    if status == Status.WAIVED:
        return waived

    member = f"{prefix}member__"
    if status == Status.COMPLETE:
        matches = (manual & Q(**{record_status: Status.COMPLETE})) | (derived & scouting_membership_q(member, as_of))
    elif status == Status.EXPIRED:
        # Nothing set by hand ever expires; only a derived requirement does.
        matches = derived & scouting_membership_q(member, as_of, expired=True)
    elif status == Status.NOT_STARTED:
        matches = (manual & Q(**{record_status: Status.NOT_STARTED})) | (
            derived
            & (
                Q(**{f"{member}scouting_membership_id": ""})
                | Q(**{f"{member}scouting_membership_expires_on__isnull": True})
            )
        )
    else:
        raise ValueError(f"Unknown status {status!r}")

    return ~waived & matches
