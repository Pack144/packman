from easy_thumbnails.files import get_thumbnailer
from rest_framework import serializers

from packman.calendars.models import PackYear
from packman.dens.models import Rank
from packman.membership.models import Scout

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


def get_avatar_url(member, is_scout=False):
    """Headshot thumbnail; None when no photo — the app renders initials instead."""
    if member.photo:
        return get_thumbnailer(member.photo).get_thumbnail({"size": (80, 80), "crop": "smart"}).url
    return None


def get_photo_url(member):
    """A larger rendition for the profile hero; None when no photo uploaded."""
    if member.photo:
        return get_thumbnailer(member.photo).get_thumbnail({"size": (640, 640), "crop": "smart"}).url
    return None


def get_rank_key(rank):
    return RANK_KEYS.get(rank.rank) if rank else None


def get_rank_badge(rank):
    return RANK_BADGES.get(rank.rank, "?") if rank else "?"


def rank_fields(rank):
    """The bundle of rank presentation fields the frontend needs everywhere."""
    return {
        "rank": rank.get_rank_display() if rank else None,
        "rank_plural": RANK_PLURALS.get(rank.rank) if rank else None,
        "rank_key": get_rank_key(rank),
        "rank_badge": get_rank_badge(rank),
        "grade": RANK_GRADE_LABELS.get(rank.rank) if rank else None,
    }


def den_label(den):
    """'Den 4 · Wolves' — the compact den designation used across the app."""
    if not den:
        return None
    plural = RANK_PLURALS.get(den.rank.rank) if den.rank else None
    return f"Den {den.number} · {plural}" if plural else f"Den {den.number}"


class ScoutBadgeSerializer(serializers.Serializer):
    """A cub's avatar + den/rank badge, used in compact listings."""

    slug = serializers.CharField()
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    den_number = serializers.SerializerMethodField()
    den_label = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    rank_key = serializers.SerializerMethodField()
    rank_badge = serializers.SerializerMethodField()

    def get_name(self, scout):
        return scout.short_name

    def get_avatar(self, scout):
        return get_avatar_url(scout, is_scout=True)

    def get_den_number(self, scout):
        den = scout.current_den
        return den.number if den else None

    def get_den_label(self, scout):
        return den_label(scout.current_den)

    def get_rank(self, scout):
        return scout.rank.get_rank_display() if scout.rank else None

    def get_rank_key(self, scout):
        return get_rank_key(scout.rank)

    def get_rank_badge(self, scout):
        return get_rank_badge(scout.rank)


class AdultSummarySerializer(serializers.Serializer):
    """A parent/guardian's name + link, used in family and roster listings."""

    slug = serializers.CharField()
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    role = serializers.CharField(source="get_role_display")

    def get_name(self, adult):
        return adult.get_full_name()

    def get_avatar(self, adult):
        return get_avatar_url(adult)


class FamilySerializer(serializers.Serializer):
    """The signed-in user's own family, for the Home screen family card."""

    name = serializers.CharField()
    adults = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    dens = serializers.SerializerMethodField()

    def get_adults(self, family):
        return AdultSummarySerializer(family.adults.all(), many=True).data

    def get_children(self, family):
        return ScoutBadgeSerializer(family.children.active(), many=True).data

    def get_dens(self, family):
        ranks = {
            scout.rank.get_rank_display() for scout in family.children.active().select_related() if scout.rank
        }
        return sorted(ranks)


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


class DenLeaderSerializer(serializers.Serializer):
    slug = serializers.CharField(source="member.slug")
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    position = serializers.CharField(source="get_position_display")
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    def get_name(self, committee_member):
        return committee_member.member.get_full_name()

    def get_avatar(self, committee_member):
        return get_avatar_url(committee_member.member)

    def get_phone(self, committee_member):
        number = committee_member.member.phone_numbers.filter(published=True).first()
        return number.number.as_e164 if number else None

    def get_email(self, committee_member):
        adult = committee_member.member
        return adult.email if adult.is_published else None


class DenRosterEntrySerializer(serializers.Serializer):
    """One row in a Den's cub/family roster."""

    scout = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()

    def get_scout(self, scout):
        return ScoutBadgeSerializer(scout).data

    def get_parents(self, scout):
        if scout.family:
            return AdultSummarySerializer(scout.family.adults.all(), many=True).data
        return []


class DenSummarySerializer(serializers.Serializer):
    """A single row in the All Dens list."""

    number = serializers.IntegerField()
    cub_count = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    my_cub = serializers.SerializerMethodField()

    def get_cub_count(self, den):
        return den.active_cubs().count()

    def get_is_mine(self, den):
        my_dens = self.context.get("my_den_numbers", set())
        return den.number in my_dens

    def get_my_cub(self, den):
        my_cubs_by_den = self.context.get("my_cubs_by_den", {})
        cub = my_cubs_by_den.get(den.number)
        return cub.short_name if cub else None

    def to_representation(self, den):
        data = super().to_representation(den)
        data.update(rank_fields(den.rank))
        return data


class DenDetailSerializer(serializers.Serializer):
    """Full detail for one Den, used by My Dens and the Den detail screen."""

    number = serializers.IntegerField()
    cub_count = serializers.SerializerMethodField()
    my_cub = serializers.SerializerMethodField()
    leaders = serializers.SerializerMethodField()
    roster = serializers.SerializerMethodField()

    def get_cub_count(self, den):
        return den.active_cubs().count()

    def get_my_cub(self, den):
        my_cubs_by_den = self.context.get("my_cubs_by_den", {})
        cub = my_cubs_by_den.get(den.number)
        return cub.short_name if cub else None

    def get_leaders(self, den):
        # A den's leaders are the committee members assigned to it for the
        # current year, reached through Den's `leadership` reverse relation
        # (CommitteeMember.den, related_name="leadership") — the same
        # mechanism the main site's DenDetailView uses. Ordered by position so
        # the Den Leader leads, followed by any Akela/assistant.
        leaders = (
            den.leadership.filter(year=PackYear.objects.current())
            .select_related("member")
            .order_by("position", "member__last_name")
        )
        return DenLeaderSerializer(leaders, many=True).data

    def get_roster(self, den):
        roster = (
            Scout.objects.filter(den_memberships__den=den, den_memberships__year_assigned=PackYear.objects.current())
            .select_related("family")
            .order_by("last_name", "first_name")
        )
        return DenRosterEntrySerializer(roster, many=True).data

    def to_representation(self, den):
        data = super().to_representation(den)
        data.update(rank_fields(den.rank))
        return data


class SearchResultSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    subtitle = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    rank_key = serializers.CharField(allow_null=True)
    rank_badge = serializers.CharField(allow_null=True)
    rank = serializers.CharField(allow_null=True)


class ContactMethodSerializer(serializers.Serializer):
    type = serializers.CharField()
    value = serializers.CharField()


class FamilyMemberSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    relation = serializers.CharField()
    rank = serializers.CharField(allow_null=True)
    rank_key = serializers.CharField(allow_null=True)


class MemberDetailSerializer(serializers.Serializer):
    """
    A single Adult or Scout's profile page. Expects a plain dict (built by
    packman.mobile.api.build_member_detail) rather than a model instance,
    since Adults and Scouts expose different contact/relation data.
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    photo = serializers.CharField(allow_null=True)
    is_scout = serializers.BooleanField()
    den = serializers.CharField(allow_null=True)
    grade = serializers.CharField(allow_null=True)
    rank = serializers.CharField(allow_null=True)
    rank_key = serializers.CharField(allow_null=True)
    phone_numbers = ContactMethodSerializer(many=True)
    emails = serializers.ListField(child=serializers.EmailField())
    family = FamilyMemberSerializer(many=True)
