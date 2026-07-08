from django.templatetags.static import static
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


def get_avatar_url(member, is_scout=False):
    if member.photo:
        return get_thumbnailer(member.photo).get_thumbnail({"size": (80, 80), "crop": "smart"}).url
    if is_scout:
        return static("img/avatar_cub_80x80.png")
    if member.gender == member.Gender.MALE:
        return static("img/avatar_man_80x80.png")
    if member.gender == member.Gender.FEMALE:
        return static("img/avatar_woman_80x80.png")
    return static("img/avatar_generic_80x80.png")


def get_rank_letter(rank):
    return rank.get_rank_display()[0].upper() if rank else "?"


class ScoutBadgeSerializer(serializers.Serializer):
    """A cub's avatar + rank badge, used in compact listings (Home, My Dens roster)."""

    slug = serializers.CharField()
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    den_number = serializers.SerializerMethodField()
    rank_letter = serializers.SerializerMethodField()

    def get_name(self, scout):
        return scout.short_name

    def get_avatar(self, scout):
        return get_avatar_url(scout, is_scout=True)

    def get_den_number(self, scout):
        den = scout.current_den
        return den.number if den else None

    def get_rank_letter(self, scout):
        return get_rank_letter(scout.rank)


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
    """The signed-in user's own family, for the Home screen 'Your Family' card."""

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


class DenLeaderSerializer(serializers.Serializer):
    slug = serializers.CharField(source="member.slug")
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    position = serializers.CharField(source="get_position_display")

    def get_name(self, committee_member):
        return committee_member.member.get_full_name()

    def get_avatar(self, committee_member):
        return get_avatar_url(committee_member.member)


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
    rank = serializers.SerializerMethodField()
    rank_letter = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    cub_count = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    my_cub = serializers.SerializerMethodField()

    def get_rank(self, den):
        return den.rank.get_rank_display() if den.rank else "Unranked"

    def get_rank_letter(self, den):
        return get_rank_letter(den.rank)

    def get_grade(self, den):
        return RANK_GRADE_LABELS.get(den.rank.rank) if den.rank else None

    def get_cub_count(self, den):
        return den.active_cubs().count()

    def get_is_mine(self, den):
        my_dens = self.context.get("my_den_numbers", set())
        return den.number in my_dens

    def get_my_cub(self, den):
        my_cubs_by_den = self.context.get("my_cubs_by_den", {})
        cub = my_cubs_by_den.get(den.number)
        return cub.short_name if cub else None


class DenDetailSerializer(serializers.Serializer):
    """Full detail for one Den, used by My Dens and the Den detail screen."""

    number = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    rank_letter = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    cub_count = serializers.SerializerMethodField()
    leaders = serializers.SerializerMethodField()
    roster = serializers.SerializerMethodField()

    def get_rank(self, den):
        return den.rank.get_rank_display() if den.rank else "Unranked"

    def get_rank_letter(self, den):
        return get_rank_letter(den.rank)

    def get_grade(self, den):
        return RANK_GRADE_LABELS.get(den.rank.rank) if den.rank else None

    def get_cub_count(self, den):
        return den.active_cubs().count()

    def get_leaders(self, den):
        leaders = self.context.get("leaders")
        if leaders is None:
            from packman.committees.models import CommitteeMember

            leaders = CommitteeMember.objects.filter(den=den, position=CommitteeMember.Position.DEN_LEADER)
        return DenLeaderSerializer(leaders, many=True).data

    def get_roster(self, den):
        roster = (
            Scout.objects.filter(den_memberships__den=den, den_memberships__year_assigned=PackYear.objects.current())
            .select_related("family")
            .order_by("last_name", "first_name")
        )
        return DenRosterEntrySerializer(roster, many=True).data


class SearchResultSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    subtitle = serializers.CharField()
    avatar = serializers.CharField()


class ContactMethodSerializer(serializers.Serializer):
    type = serializers.CharField()
    value = serializers.CharField()


class FamilyMemberSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    avatar = serializers.CharField()
    relation = serializers.CharField()


class MemberDetailSerializer(serializers.Serializer):
    """
    A single Adult or Scout's profile page. Expects a plain dict (built by
    packman.mobile.api.build_member_detail) rather than a model instance,
    since Adults and Scouts expose different contact/relation data.
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    avatar = serializers.CharField()
    is_scout = serializers.BooleanField()
    den = serializers.CharField(allow_null=True)
    rank_letter = serializers.CharField(allow_null=True)
    phone_numbers = ContactMethodSerializer(many=True)
    emails = serializers.ListField(child=serializers.EmailField())
    family = FamilyMemberSerializer(many=True)
