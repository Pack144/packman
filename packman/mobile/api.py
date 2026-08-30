from collections import defaultdict

from django.conf import settings
from django.db.models import Q, Value
from django.db.models.functions import Coalesce, NullIf
from django.utils import timezone

from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from packman.calendars.models import Event, PackYear
from packman.committees.leadership import LEADERSHIP_TITLES, assignment_title
from packman.committees.models import Committee, CommitteeMember
from packman.compliance.summaries import summarize_family
from packman.dens.models import Den, Membership
from packman.membership.models import Adult, Family, Member, Scout

from .permissions import IsActiveMemberOrContributor
from .serializers import (
    DirectorySerializer,
    EventSerializer,
    FamilyRequirementsSerializer,
    get_avatar_url,
    get_photo_url,
    rank_fields,
)


def visible_members():
    """
    Members who belong to a currently active family, or are contributors.
    This is the directory's member visibility rule: anyone outside it is
    'active': False in the directory payload (and, if they aren't part of a
    still-visible family either, absent from it altogether).
    """
    return Member.objects.filter(
        Q(adult__family__children__status__exact=Scout.ACTIVE)
        | Q(adult__role__exact=Adult.CONTRIBUTOR)
        | Q(scout__status__exact=Scout.ACTIVE)
    ).distinct()


def _scout_entry_fields(member, den):
    """
    Rank/grade aren't included here — they always match the den this scout's
    `den_number` points to (see DirectoryMemberSerializer), so the frontend
    resolves them from `dens[]` instead of the wire repeating them per scout.
    """
    scout = member.scout
    return {
        "is_scout": True,
        "title": None,
        "role": None,
        "phone_numbers": [],
        "emails": [],
        "den_number": den.number if den else None,
        "family_slug": str(scout.family_id) if scout.family_id else None,
    }


def _adult_entry_fields(member, title):
    adult = member.adult
    return {
        "is_scout": False,
        "title": title,
        "role": adult.get_role_display(),
        # .all() reads from the prefetch cache built in build_directory();
        # filtering here in Python (rather than .filter(published=True))
        # avoids a fresh query per adult.
        "phone_numbers": [
            {"type": pn.get_type_display() or "Phone", "value": pn.number.as_national}
            for pn in adult.phone_numbers.all()
            if pn.published
        ],
        "emails": [adult.email] if adult.is_published else [],
        "den_number": None,
        "family_slug": str(adult.family_id) if adult.family_id else None,
    }


def _build_member_entry(member, *, active, den, title):
    entry = {
        "slug": member.slug,
        "name": member.get_full_name(),
        "short_name": member.short_name,
        "avatar": get_avatar_url(member),
        "photo": get_photo_url(member),
        "active": active,
        # Visibility scope (visible_members()) is exactly what MemberDetailView
        # used to gate on; a member outside it has no profile to link to.
        "linkable": active,
    }
    if hasattr(member, "scout"):
        entry.update(_scout_entry_fields(member, den))
    else:
        entry.update(_adult_entry_fields(member, title))
    return entry


def _build_members_payload(members, *, base_ids, current_year):
    scout_pks = [m.pk for m in members if hasattr(m, "scout")]
    den_by_scout = {
        membership.scout_id: membership.den
        for membership in Membership.objects.filter(scout_id__in=scout_pks, year_assigned=current_year).select_related(
            "den", "den__rank"
        )
    }

    # One query for every adult's current-year committee assignments, rather
    # than the per-adult query packman.committees.leadership.leadership_title()
    # would cost if called once per member.
    adult_pks = [m.pk for m in members if hasattr(m, "adult")]
    titles_by_adult = defaultdict(set)
    for assignment in CommitteeMember.objects.filter(member_id__in=adult_pks, year=current_year).select_related(
        "committee"
    ):
        if title := assignment_title(assignment):
            titles_by_adult[assignment.member_id].add(title)
    senior_title_by_adult = {
        pk: next((title for title in LEADERSHIP_TITLES.values() if title in titles), None)
        for pk, titles in titles_by_adult.items()
    }

    return [
        _build_member_entry(
            member,
            active=member.pk in base_ids,
            den=den_by_scout.get(member.pk),
            title=senior_title_by_adult.get(member.pk),
        )
        for member in members
    ]


def _build_dens_payload(current_year):
    dens = Den.objects.current().select_related("rank").order_by("rank__rank", "number")

    leaders_by_den = defaultdict(list)
    leader_rows = (
        CommitteeMember.objects.filter(den__isnull=False, year=current_year)
        .select_related("member")
        .order_by("position", "member__last_name")
    )
    for row in leader_rows:
        leaders_by_den[row.den_id].append(
            {
                "slug": row.member.slug,
                "position": row.get_position_display(),
                "name": row.member.get_full_name(),
                # Den leaders are always drawn from a current-year Den
                # assignment (see Den.objects.current()), so unlike a
                # committee's membership history there's no "left the pack
                # entirely since" case worth a `linked` flag for.
            }
        )

    payload = []
    for den in dens:
        roster = list(
            Scout.objects.filter(den_memberships__den=den, den_memberships__year_assigned=current_year)
            # Sorted by the name the roster row actually shows — short_name,
            # which is the nickname when there is one.
            .annotate(sort_name=Coalesce(NullIf("nickname", Value("")), "first_name"))
            .order_by("sort_name", "last_name")
            .values_list("slug", flat=True)
        )
        entry = {"number": den.number, "leaders": leaders_by_den.get(den.number, []), "roster": roster}
        entry.update(rank_fields(den.rank))
        payload.append(entry)
    return payload


def _build_committees_payload(current_year, payload_ids):
    # Only the last 5 calendar years of committee history travel in every
    # load — older assignments aren't worth the weight. Calendar years, not
    # "the 5 most recent PackYear rows on file": PackYear rows are created
    # lazily, so a Pack with gaps could otherwise pull in a much older year.
    recent_year_ids = set(range(current_year.year - 4, current_year.year + 1))
    recent_years = list(PackYear.objects.filter(year__in=recent_year_ids).order_by("-year"))

    committees = Committee.objects.by_years(recent_years)

    payload = []
    for committee in committees:
        years_with_roster = list(
            PackYear.objects.filter(committee_membership__committee=committee, year__in=recent_year_ids)
            .distinct()
            .order_by("-start_date")
        )
        membership = {}
        for year in years_with_roster:
            rows = (
                committee.committee_members.filter(year=year).select_related("member")
                # Lower Position values are more senior (Chair=1 ... Assistant
                # Akela=6); rows arrive in this order and are grouped below
                # without disturbing it, so the frontend never re-sorts.
                .order_by("position", "member__last_name")
            )
            by_position = {}
            for row in rows:
                by_position.setdefault(row.get_position_display(), []).append(
                    {
                        "slug": row.member.slug,
                        "name": row.member.get_full_name(),
                        # A committee spans years; someone who served a while ago
                        # may since have left the pack entirely — not just gone
                        # inactive within a still-tracked family, but absent from
                        # `members` altogether. `linked: false` says "there's no
                        # member entry to look this slug up in."
                        "linked": row.member_id in payload_ids,
                    }
                )
            membership[str(year.year)] = by_position

        payload.append(
            {
                "slug": committee.slug,
                "name": committee.name,
                "description": committee.description,
                "leadership": committee.leadership,
                # Just the ending year of each PackYear, newest first; a Pack
                # Year always runs <year - 1>-<year>, so the frontend builds
                # a display label from the int rather than the wire spelling
                # it out for every committee.
                "years": [year.year for year in years_with_roster],
                "membership": membership,
            }
        )
    return payload


def _find_current_akela(current_year):
    """
    The slug of whoever holds the Pack's 'Akela' title this year, or None.

    Goes through assignment_title() rather than filtering on
    CommitteeMember.Position.AKELA directly: a Pack can also grant the title
    via a committee named 'Akelas' whose members sit at the default Member
    position (see packman.committees.leadership.assignment_title's
    committee-name fallback) — that assignment wouldn't have position==AKELA,
    but it does carry the "Akela" title and must resolve to the same person.
    """
    rows = (
        CommitteeMember.objects.filter(year=current_year)
        .select_related("member", "committee")
        .order_by("member__last_name")
    )
    for row in rows:
        if assignment_title(row) == CommitteeMember.Position.AKELA.label:
            return row.member.slug
    return None


def build_directory(user):
    current_year = PackYear.objects.current()

    base_qs = visible_members()
    base_ids = set(base_qs.values_list("pk", flat=True))

    # A profile only exists for visible_members(), but their inactive family
    # (a graduated sibling, a non-contributor co-parent) still needs to be
    # nameable on a family card — so the payload widens to include them too,
    # each marked active/linkable False.
    family_ids = set(
        Family.objects.filter(Q(adults__pk__in=base_ids) | Q(children__pk__in=base_ids)).values_list("pk", flat=True)
    )
    members = list(
        Member.objects.filter(Q(pk__in=base_ids) | Q(adult__family__in=family_ids) | Q(scout__family__in=family_ids))
        .distinct()
        .select_related("adult", "scout", "adult__family", "scout__family")
        .prefetch_related("adult__phone_numbers")
    )
    payload_ids = {member.pk for member in members}

    return {
        "viewer": user.slug,
        "current_year": current_year.year,
        "akela": _find_current_akela(current_year),
        "pack": {"name": settings.PACK_NAME, "location": settings.PACK_LOCATION},
        "members": _build_members_payload(members, base_ids=base_ids, current_year=current_year),
        "dens": _build_dens_payload(current_year),
        "committees": _build_committees_payload(current_year, payload_ids),
    }


class DirectoryView(GenericAPIView):
    """
    The mobile PWA's single data call: every visible member, den and
    committee (last 5 years), plus `viewer` — the caller's own slug within
    `members`. See packman/mobile/static/mobile/js/api.js's getDirectory()
    for how the frontend turns this into local lookups for every screen.
    """

    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        return Response(DirectorySerializer(build_directory(request.user)).data)


class EventView(GenericAPIView):
    """
    The next upcoming (or just-started) Pack event, for Home's 'Coming Up'
    card. Kept separate from DirectoryView because an event's freshness
    matters on its own schedule, not the directory's.
    """

    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        # Keep showing an event already in progress (started within the last
        # 8 hours), like the main site's home page does.
        event = (
            Event.objects.filter(
                start__gte=timezone.now() - timezone.timedelta(hours=8),
                status=Event.CONFIRMED,
                published=True,
            )
            .order_by("start")
            .first()
        )
        return Response({"event": EventSerializer(event).data if event else None})


def build_family_requirements(user):
    """
    The viewer's own family's requirements for the current pack year.

    Kept out of build_directory() on purpose: that payload is shared with
    every member of the pack, and a family's paperwork is theirs alone.
    """
    summary = summarize_family(user.family)
    groups = []
    for group in summary["groups"]:
        subject = group["subject"]
        groups.append(
            {
                "name": str(subject),
                # The household group is a Family, which has no profile page.
                "slug": getattr(subject, "slug", None),
                "records": [
                    {
                        "requirement": record.requirement.name,
                        "status": record.effective_status.value,
                        "status_label": record.effective_status.label,
                        "expires_on": record.expires_on,
                    }
                    for record in group["records"]
                ],
            }
        )

    year = summary["year"]
    return {
        "year_label": str(year) if year else "",
        "outstanding": len(summary["outstanding"]),
        "groups": groups,
    }


class RequirementsView(GenericAPIView):
    """
    The signed-in member's family requirements, for the bottom of the Me
    screen. Separate from DirectoryView because it is scoped to one family
    and changes on a different cadence than the roster.
    """

    permission_classes = [IsActiveMemberOrContributor]

    def get(self, request):
        return Response(FamilyRequirementsSerializer(build_family_requirements(request.user)).data)
