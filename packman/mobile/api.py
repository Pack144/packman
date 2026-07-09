from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from packman.calendars.models import Event
from packman.dens.models import Den
from packman.membership.models import Adult, Member, Scout

from .permissions import IsActiveMemberOrContributor
from .serializers import (
    DenDetailSerializer,
    DenSummarySerializer,
    EventSerializer,
    FamilySerializer,
    MemberDetailSerializer,
    SearchResultSerializer,
    den_label,
    get_avatar_url,
    get_photo_url,
    get_rank_badge,
    get_rank_key,
)


def visible_adults():
    """
    Adults in a currently active family, or contributors — the directory's
    adult visibility rule, shared by member lookup and search.
    """
    return Adult.objects.filter(
        Q(family__children__status__exact=Scout.ACTIVE) | Q(role__exact=Adult.CONTRIBUTOR)
    )


def visible_members():
    """
    Members who belong to a currently active family, or are contributors.
    Mirrors packman.membership.views.MemberList's visibility rule (and the
    adult half of visible_adults()).
    """
    return Member.objects.filter(
        Q(adult__family__children__status__exact=Scout.ACTIVE)
        | Q(adult__role__exact=Adult.CONTRIBUTOR)
        | Q(scout__status__exact=Scout.ACTIVE)
    ).distinct()


def scout_den_label(scout):
    return den_label(scout.current_den)


def build_member_detail(member):
    """Build the polymorphic profile payload for either an Adult or a Scout."""
    if hasattr(member, "scout"):
        scout = member.scout
        family = []
        if scout.family:
            family.extend(
                {
                    "slug": adult.slug,
                    "name": adult.get_full_name(),
                    "avatar": get_avatar_url(adult),
                    "relation": adult.get_role_display(),
                    "rank": None,
                    "rank_key": None,
                }
                for adult in scout.family.adults.all()
            )
            for sibling in scout.get_siblings() or []:
                sibling_den = scout_den_label(sibling)
                family.append(
                    {
                        "slug": sibling.slug,
                        "name": sibling.get_full_name(),
                        "avatar": get_avatar_url(sibling),
                        "relation": f"Sibling · {sibling_den}" if sibling_den else "Sibling",
                        "rank": sibling.rank.get_rank_display() if sibling.rank else None,
                        "rank_key": get_rank_key(sibling.rank),
                    }
                )
        return {
            "slug": scout.slug,
            "name": scout.get_full_name(),
            "avatar": get_avatar_url(scout),
            "photo": get_photo_url(scout),
            "is_scout": True,
            "den": scout_den_label(scout),
            "grade": str(scout.grade).title() if scout.grade else None,
            "rank": scout.rank.get_rank_display() if scout.rank else None,
            "rank_key": get_rank_key(scout.rank),
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
                "rank": None,
                "rank_key": None,
            }
            for partner in adult.get_partners() or []
        )
        for child in adult.family.children.active():
            child_den = scout_den_label(child)
            family.append(
                {
                    "slug": child.slug,
                    "name": child.get_full_name(),
                    "avatar": get_avatar_url(child),
                    "relation": f"Cub · {child_den}" if child_den else "Cub",
                    "rank": child.rank.get_rank_display() if child.rank else None,
                    "rank_key": get_rank_key(child.rank),
                }
            )
    return {
        "slug": adult.slug,
        "name": adult.get_full_name(),
        "avatar": get_avatar_url(adult),
        "photo": get_photo_url(adult),
        "is_scout": False,
        "den": None,
        "grade": None,
        "rank": None,
        "rank_key": None,
        "phone_numbers": phone_numbers,
        "emails": [adult.email] if adult.is_published else [],
        "family": family,
    }


def my_cubs_by_den(user):
    scouts = user.get_active_scouts() or Scout.objects.none()
    return {scout.current_den.number: scout for scout in scouts if scout.current_den}


class HomeView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        user = request.user
        family = FamilySerializer(user.family).data if user.family else None

        # The next confirmed event; keep showing one already in progress
        # (started within the last 8 hours) like the site's home page does.
        event = (
            Event.objects.filter(
                start__gte=timezone.now() - timezone.timedelta(hours=8),
                status=Event.CONFIRMED,
                published=True,
            )
            .order_by("start")
            .first()
        )

        return Response(
            {
                "pack": {
                    "name": settings.PACK_NAME,
                    "location": settings.PACK_LOCATION,
                },
                "user": {"slug": user.slug, "name": user.get_full_name(), "short_name": user.short_name},
                "family": family,
                "event": EventSerializer(event).data if event else None,
            }
        )


class MyDensView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        cubs_by_den = my_cubs_by_den(request.user)
        den_numbers = sorted(cubs_by_den)
        dens = Den.objects.filter(number__in=den_numbers).select_related("rank")
        dens_by_number = {den.number: den for den in dens}
        ordered = [dens_by_number[number] for number in den_numbers]
        context = {"my_cubs_by_den": cubs_by_den}
        return Response(
            {
                "cub_count": len(request.user.get_active_scouts() or []),
                "dens": DenDetailSerializer(ordered, many=True, context=context).data,
            }
        )


class DenListView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        cubs_by_den = my_cubs_by_den(request.user)
        dens = Den.objects.current().select_related("rank").order_by("rank__rank", "number")
        context = {"my_den_numbers": set(cubs_by_den), "my_cubs_by_den": cubs_by_den}
        return Response({"dens": DenSummarySerializer(dens, many=True, context=context).data})


class DenDetailView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request, number):
        den = get_object_or_404(Den.objects.current(), number=number)
        context = {"my_cubs_by_den": my_cubs_by_den(request.user)}
        return Response(DenDetailSerializer(den, context=context).data)


class SearchView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        result_type = request.query_params.get("type", "all")
        cubs = []
        parents = []

        if query:
            name_filter = (
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(middle_name__icontains=query)
                | Q(nickname__icontains=query)
            )

            if result_type in ("all", "cub"):
                for scout in Scout.objects.active().filter(name_filter).distinct():
                    cubs.append(
                        {
                            "slug": scout.slug,
                            "name": scout.get_full_name(),
                            "type": "cub",
                            "subtitle": scout_den_label(scout) or "",
                            "avatar": get_avatar_url(scout),
                            "rank": scout.rank.get_rank_display() if scout.rank else None,
                            "rank_key": get_rank_key(scout.rank),
                            "rank_badge": get_rank_badge(scout.rank) if scout.rank else None,
                        }
                    )

            if result_type in ("all", "parent"):
                adults = visible_adults().filter(name_filter).distinct()
                for adult in adults:
                    active_cubs = adult.get_active_scouts()
                    if active_cubs:
                        names = ", ".join(c.short_name for c in active_cubs)
                        subtitle = f"Parent of {names}"
                    else:
                        subtitle = adult.get_role_display()
                    parents.append(
                        {
                            "slug": adult.slug,
                            "name": adult.get_full_name(),
                            "type": "parent",
                            "subtitle": subtitle,
                            "avatar": get_avatar_url(adult),
                            "rank": None,
                            "rank_key": None,
                            "rank_badge": None,
                        }
                    )

        return Response(
            {
                "cubs": SearchResultSerializer(cubs, many=True).data,
                "parents": SearchResultSerializer(parents, many=True).data,
                # Kept for any client still reading the flat list.
                "results": SearchResultSerializer(cubs + parents, many=True).data,
            }
        )


class MemberDetailView(GenericAPIView):
    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request, slug):
        member = get_object_or_404(visible_members(), slug=slug)
        return Response(MemberDetailSerializer(build_member_detail(member)).data)
