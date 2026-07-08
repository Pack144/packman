from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from packman.calendars.models import PackYear
from packman.committees.models import CommitteeMember
from packman.dens.models import Den
from packman.membership.models import Adult, Member, Scout

from .permissions import IsActiveMemberOrContributor
from .serializers import (
    DenDetailSerializer,
    DenSummarySerializer,
    FamilySerializer,
    MemberDetailSerializer,
    SearchResultSerializer,
    get_avatar_url,
    get_rank_letter,
)


def visible_members():
    """
    Members who belong to a currently active family, or are contributors.
    Mirrors packman.membership.views.MemberList's visibility rule.
    """
    return Member.objects.filter(
        Q(adult__family__children__status__exact=Scout.ACTIVE)
        | Q(adult__role__exact=Adult.CONTRIBUTOR)
        | Q(scout__status__exact=Scout.ACTIVE)
    ).distinct()


def build_member_detail(member):
    """Build the polymorphic profile payload for either an Adult or a Scout."""
    if hasattr(member, "scout"):
        scout = member.scout
        den = scout.current_den
        family = []
        if scout.family:
            family.extend(
                {
                    "slug": adult.slug,
                    "name": adult.get_full_name(),
                    "avatar": get_avatar_url(adult),
                    "relation": adult.get_role_display(),
                }
                for adult in scout.family.adults.all()
            )
            family.extend(
                {
                    "slug": sibling.slug,
                    "name": sibling.get_full_name(),
                    "avatar": get_avatar_url(sibling, is_scout=True),
                    "relation": "Sibling",
                }
                for sibling in scout.get_siblings() or []
            )
        return {
            "slug": scout.slug,
            "name": scout.get_full_name(),
            "avatar": get_avatar_url(scout, is_scout=True),
            "is_scout": True,
            "den": str(den) if den else None,
            "rank_letter": get_rank_letter(scout.rank) if scout.rank else None,
            "phone_numbers": [],
            "emails": [],
            "family": family,
        }

    adult = member.adult
    phone_numbers = [
        {"type": pn.get_type_display() or "Phone", "value": pn.number.as_national}
        for pn in adult.phone_numbers.filter(published=True)
    ]
    family = []
    if adult.family:
        family.extend(
            {
                "slug": partner.slug,
                "name": partner.get_full_name(),
                "avatar": get_avatar_url(partner),
                "relation": partner.get_role_display(),
            }
            for partner in adult.get_partners() or []
        )
        family.extend(
            {
                "slug": child.slug,
                "name": child.get_full_name(),
                "avatar": get_avatar_url(child, is_scout=True),
                "relation": "Cub",
            }
            for child in adult.family.children.active()
        )
    return {
        "slug": adult.slug,
        "name": adult.get_full_name(),
        "avatar": get_avatar_url(adult),
        "is_scout": False,
        "den": None,
        "rank_letter": None,
        "phone_numbers": phone_numbers,
        "emails": [adult.email] if adult.is_published else [],
        "family": family,
    }


class HomeView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        user = request.user
        family = FamilySerializer(user.family).data if user.family else None
        return Response(
            {
                "user": {"slug": user.slug, "name": user.get_full_name()},
                "family": family,
            }
        )


class MyDensView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        scouts = request.user.get_active_scouts() or Scout.objects.none()
        den_numbers = sorted({scout.current_den.number for scout in scouts if scout.current_den})
        dens = Den.objects.filter(number__in=den_numbers)
        dens_by_number = {den.number: den for den in dens}
        ordered = [dens_by_number[number] for number in den_numbers]
        return Response({"dens": DenDetailSerializer(ordered, many=True).data})


class DenListView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        scouts = request.user.get_active_scouts() or Scout.objects.none()
        my_cubs_by_den = {scout.current_den.number: scout for scout in scouts if scout.current_den}
        dens = Den.objects.current().select_related("rank").order_by("rank__rank", "number")
        context = {"my_den_numbers": set(my_cubs_by_den), "my_cubs_by_den": my_cubs_by_den}
        return Response({"dens": DenSummarySerializer(dens, many=True, context=context).data})


class DenDetailView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request, number):
        den = get_object_or_404(Den.objects.current(), number=number)
        leaders = CommitteeMember.objects.filter(
            den=den,
            year=PackYear.objects.current(),
            position=CommitteeMember.Position.DEN_LEADER,
        )
        return Response(DenDetailSerializer(den, context={"leaders": leaders}).data)


class SearchView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        result_type = request.query_params.get("type", "all")
        results = []

        if query:
            name_filter = (
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(middle_name__icontains=query)
                | Q(nickname__icontains=query)
            )

            if result_type in ("all", "cub"):
                for scout in Scout.objects.active().filter(name_filter).distinct():
                    results.append(
                        {
                            "slug": scout.slug,
                            "name": scout.get_full_name(),
                            "type": "cub",
                            "subtitle": scout.rank.get_rank_display() if scout.rank else "",
                            "avatar": get_avatar_url(scout, is_scout=True),
                        }
                    )

            if result_type in ("all", "parent"):
                adults = Adult.objects.filter(name_filter).filter(
                    Q(family__children__status__exact=Scout.ACTIVE) | Q(role__exact=Adult.CONTRIBUTOR)
                ).distinct()
                for adult in adults:
                    cubs = adult.get_active_scouts()
                    subtitle = f"Parent of {', '.join(c.short_name for c in cubs)}" if cubs else "Parent"
                    results.append(
                        {
                            "slug": adult.slug,
                            "name": adult.get_full_name(),
                            "type": "parent",
                            "subtitle": subtitle,
                            "avatar": get_avatar_url(adult),
                        }
                    )

        return Response({"results": SearchResultSerializer(results, many=True).data})


class MemberDetailView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request, slug):
        member = get_object_or_404(visible_members(), slug=slug)
        return Response(MemberDetailSerializer(build_member_detail(member)).data)
