import logging

from easy_thumbnails.files import get_thumbnailer
from rest_framework import serializers

from packman.dens.models import Rank

logger = logging.getLogger(__name__)

# BSA's cub scout program ties each rank to a specific school grade.
RANK_GRADE_LABELS = {
    Rank.RankChoices.LION: "Kindergarten",
    Rank.RankChoices.TIGER: "1st Grade",
    Rank.RankChoices.WOLF: "2nd Grade",
    Rank.RankChoices.BEAR: "3rd Grade",
    Rank.RankChoices.JR_WEBE: "4th Grade",
    Rank.RankChoices.SR_WEBE: "5th Grade",
    Rank.RankChoices.WEBE: "Webelos",
    Rank.RankChoices.ARROW: "5th Grade",
}

# Stable keys the frontend maps to the Pack 144 rank color palette.
RANK_KEYS = {
    Rank.RankChoices.LION: "lion",
    Rank.RankChoices.TIGER: "tiger",
    Rank.RankChoices.WOLF: "wolf",
    Rank.RankChoices.BEAR: "bear",
    Rank.RankChoices.JR_WEBE: "webelos",
    Rank.RankChoices.SR_WEBE: "webelos",
    Rank.RankChoices.WEBE: "webelos",
    Rank.RankChoices.ARROW: "aol",
}

RANK_BADGES = {
    Rank.RankChoices.LION: "L",
    Rank.RankChoices.TIGER: "T",
    Rank.RankChoices.WOLF: "W",
    Rank.RankChoices.BEAR: "B",
    Rank.RankChoices.JR_WEBE: "We",
    Rank.RankChoices.SR_WEBE: "We",
    Rank.RankChoices.WEBE: "We",
    Rank.RankChoices.ARROW: "A",
}

RANK_PLURALS = {
    Rank.RankChoices.LION: "Lions",
    Rank.RankChoices.TIGER: "Tigers",
    Rank.RankChoices.WOLF: "Wolves",
    Rank.RankChoices.BEAR: "Bears",
    Rank.RankChoices.JR_WEBE: "Jr. Webelos",
    Rank.RankChoices.SR_WEBE: "Sr. Webelos",
    Rank.RankChoices.WEBE: "Webelos",
    Rank.RankChoices.ARROW: "AOL",
}


def get_avatar_url(member):
    """Headshot thumbnail; None when no photo — the app renders initials instead."""
    return _thumbnail_url(member, size=(80, 80))


def get_photo_url(member):
    """A larger rendition for the profile hero; None when no photo uploaded."""
    return _thumbnail_url(member, size=(640, 640))


def _thumbnail_url(member, *, size):
    """
    A cropped thumbnail URL for `member.photo`, or None when there's no photo
    — or when the file on disk can't actually be read as one. One member's
    corrupt/missing upload shouldn't 500 the whole directory for everyone
    else, so a broken photo is treated the same as no photo at all.

    Deliberately broad: easy_thumbnails/Pillow surface a variety of
    exception types for "this isn't a readable image" (missing file, wrong
    format, a source generator raising its own error, ...) and every one of
    them should degrade the same way here.
    """
    if not member.photo:
        return None
    try:
        return get_thumbnailer(member.photo).get_thumbnail({"size": size, "crop": "smart"}).url
    except Exception:
        logger.warning("Could not generate a thumbnail for %r; treating as no photo.", member.photo.name)
        return None


def get_rank_key(rank):
    return RANK_KEYS.get(rank.rank) if rank else None


def get_rank_badge(rank):
    return RANK_BADGES.get(rank.rank, "?") if rank else "?"


def get_rank_plural(rank):
    return RANK_PLURALS.get(rank.rank) if rank else None


def rank_fields(rank):
    """The bundle of rank presentation fields the frontend needs everywhere."""
    return {
        "rank": rank.get_rank_display() if rank else None,
        "rank_plural": get_rank_plural(rank),
        "rank_key": get_rank_key(rank),
        "rank_badge": get_rank_badge(rank),
        "grade": RANK_GRADE_LABELS.get(rank.rank) if rank else None,
    }


class EventSerializer(serializers.Serializer):
    """The next upcoming pack event, for the Home screen 'Coming Up' card."""

    name = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField(allow_null=True)
    location = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_location(self, event):
        if event.venue:
            return event.venue.name
        return event.location or None

    def get_description(self, event):
        from django.utils.html import strip_tags

        if not event.description:
            return None
        text = strip_tags(event.description).strip()
        return text[:140] or None


class ContactMethodSerializer(serializers.Serializer):
    type = serializers.CharField()
    value = serializers.CharField()


class DirectoryMemberSerializer(serializers.Serializer):
    """
    One row in the single-call directory's `members` list — an Adult or a
    Scout, flattened into one shape. Scout-only fields are null for adults
    and vice versa; the frontend tells them apart with `is_scout`.
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    short_name = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    photo = serializers.CharField(allow_null=True)
    is_scout = serializers.BooleanField()
    # False for a graduated/withdrawn scout, or an adult with no active cub
    # who isn't a contributor — kept only so a family card can still name them.
    active = serializers.BooleanField()
    # False whenever `active` is False: there's no profile to link to.
    linkable = serializers.BooleanField()

    # Adult-only fields.
    title = serializers.CharField(allow_null=True)
    role = serializers.CharField(allow_null=True)
    phone_numbers = ContactMethodSerializer(many=True)
    emails = serializers.ListField(child=serializers.EmailField())

    # Scout-only fields. Rank/grade aren't repeated here — they always match
    # the den (`dens[].rank`/`rank_plural`/`rank_key`/`rank_badge`/`grade`)
    # this scout's `den_number` points to, so the frontend resolves them from
    # there instead of the wire duplicating the same value per scout.
    den_number = serializers.IntegerField(allow_null=True)

    # Opaque id grouping related members; null for a member with no family on
    # file. The frontend groups by this to render family/roster relations.
    family_slug = serializers.CharField(allow_null=True)


class DenLeaderRefSerializer(serializers.Serializer):
    """
    A den leadership assignment. Unlike a committee membership row, a den
    leader is assumed to always be a linked, visible member — there's no
    `linked` flag here; a leader who somehow isn't in `members` is a data
    bug to fix, not a case the frontend needs to render around.
    """

    slug = serializers.CharField()
    position = serializers.CharField()
    name = serializers.CharField()


class DirectoryDenSerializer(serializers.Serializer):
    """A single Den, current Pack Year only — every den member is guaranteed
    to be in `members`, so `roster` is a plain list of scout slugs."""

    number = serializers.IntegerField()
    rank = serializers.CharField(allow_null=True)
    rank_plural = serializers.CharField(allow_null=True)
    rank_key = serializers.CharField(allow_null=True)
    rank_badge = serializers.CharField(allow_null=True)
    grade = serializers.CharField(allow_null=True)
    leaders = DenLeaderRefSerializer(many=True)
    roster = serializers.ListField(child=serializers.CharField())


class CommitteeMembershipEntrySerializer(serializers.Serializer):
    """
    One assigned member row for a single committee year, grouped under its
    `position` in the parent map (see DirectoryCommitteeSerializer.membership)
    — the position isn't repeated on the entry itself. `linked` is False
    when the member has since left the pack entirely and isn't in `members`
    — `name` is inlined here because it's the only place left to get it from.
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    linked = serializers.BooleanField()


class DirectoryCommitteeSerializer(serializers.Serializer):
    """A Committee and its last 5 years of membership history."""

    slug = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    leadership = serializers.BooleanField()
    # Just the PackYear ending years, newest first; a Pack Year always runs
    # <year - 1>-<year>, so the frontend builds a display label from the
    # int itself instead of the wire spelling it out for every committee.
    years = serializers.ListField(child=serializers.IntegerField())
    # Keyed by year (as a string, since JSON object keys are always strings),
    # then by that year's position label (e.g. "Chair", "Den Leader") — a
    # flat list per position, server-ordered (lowest Position value, i.e.
    # most senior, first; then by name) rather than the frontend having to
    # re-derive groupings from a raw position code.
    membership = serializers.DictField(
        child=serializers.DictField(child=CommitteeMembershipEntrySerializer(many=True))
    )


class PackSerializer(serializers.Serializer):
    name = serializers.CharField()
    location = serializers.CharField()


class DirectorySerializer(serializers.Serializer):
    """The mobile PWA's single data call — see packman.mobile.api.DirectoryView."""

    viewer = serializers.CharField()
    current_year = serializers.IntegerField()
    # Slug of whoever holds the Pack's "Akela" title this year, mirroring
    # `viewer` — the frontend resolves it against `members`/`committees`
    # instead of re-deriving it from committee position/title text itself.
    akela = serializers.CharField(allow_null=True)
    pack = PackSerializer()
    members = DirectoryMemberSerializer(many=True)
    dens = DirectoryDenSerializer(many=True)
    committees = DirectoryCommitteeSerializer(many=True)
