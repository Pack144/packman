import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image

from packman.address_book.models import PhoneNumber
from packman.calendars.models import Category, Event, PackYear
from packman.committees.models import Committee, CommitteeMember
from packman.dens.factories import DenFactory
from packman.dens.models import Membership, Rank
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory
from packman.membership.models import Adult, Scout

from .base import MobileDirectoryTestCase


def photo_upload(name="headshot.png"):
    """A small real image, so easy_thumbnails has something to resize."""
    buffer = BytesIO()
    Image.new("RGB", (200, 200), "navy").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class EventAPITestCase(MobileDirectoryTestCase):
    def test_anonymous_is_forbidden(self):
        response = self.client.get(reverse("mobile:api-event"))
        self.assertEqual(response.status_code, 403)

    def test_returns_the_next_upcoming_event(self):
        category = Category.objects.create(name="Pack Event")
        Event.objects.create(
            name="Wallingford Parade",
            start=timezone.now() + timezone.timedelta(days=2),
            end=timezone.now() + timezone.timedelta(days=2, hours=2),
            location="Wallingford",
            category=category,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-event")).json()
        self.assertEqual(data["event"]["name"], "Wallingford Parade")
        self.assertEqual(data["event"]["location"], "Wallingford")

    def test_returns_an_event_already_in_progress(self):
        # An event that started within the last 8 hours is still surfaced.
        category = Category.objects.create(name="Pack Event")
        Event.objects.create(
            name="Blue & Gold Banquet",
            start=timezone.now() - timezone.timedelta(hours=1),
            end=timezone.now() + timezone.timedelta(hours=1),
            location="Fellowship Hall",
            category=category,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-event")).json()
        self.assertEqual(data["event"]["name"], "Blue & Gold Banquet")

    def test_event_past_the_eight_hour_window_is_not_returned(self):
        category = Category.objects.create(name="Pack Event")
        Event.objects.create(
            name="Yesterday's Meeting",
            start=timezone.now() - timezone.timedelta(hours=9),
            end=timezone.now() - timezone.timedelta(hours=8),
            location="Fellowship Hall",
            category=category,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-event")).json()
        self.assertIsNone(data["event"])

    def test_no_event_returns_null(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-event")).json()
        self.assertIsNone(data["event"])


class DirectoryAPITestCase(MobileDirectoryTestCase):
    def get_directory(self):
        return self.client.get(reverse("mobile:api-directory")).json()

    def member(self, data, slug):
        return next(m for m in data["members"] if m["slug"] == slug)

    def test_anonymous_is_forbidden(self):
        response = self.client.get(reverse("mobile:api-directory"))
        self.assertEqual(response.status_code, 403)

    def test_viewer_points_to_the_signed_in_member(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(data["viewer"], self.parent.slug)
        self.assertTrue(any(m["slug"] == self.parent.slug for m in data["members"]))

    def test_pack_info_is_present(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIn("name", data["pack"])
        self.assertIn("location", data["pack"])

    def test_current_year_is_reported(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(data["current_year"], self.pack_year.year)

    def test_akela_is_null_when_nobody_holds_the_title(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIsNone(data["akela"])

    def test_akela_points_to_the_position_based_akela(self):
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(data["akela"], self.parent.slug)

    def test_akela_points_to_a_committee_name_fallback_akela(self):
        # No AKELA position row at all — the title comes purely from the
        # committee being flagged leadership=True and named "Akela".
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(committee=committee, member=self.parent, year=self.pack_year)
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(data["akela"], self.parent.slug)

    def test_akela_ignores_an_assistant_akela(self):
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=self.pack_year,
            position=CommitteeMember.Position.ASSISTANT_AKELA,
        )
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIsNone(data["akela"])

    def test_akela_from_a_prior_year_is_not_reported(self):
        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=last_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIsNone(data["akela"])

    def test_scout_member_carries_den_number_but_not_rank_fields(self):
        """
        Rank/grade live only on the den entry (dens[].rank/.../grade) that
        this scout's den_number points to — a member row doesn't repeat them.
        """
        self.client.force_login(self.parent)
        data = self.get_directory()
        scout = self.member(data, self.scout.slug)
        self.assertTrue(scout["is_scout"])
        self.assertTrue(scout["active"])
        self.assertTrue(scout["linkable"])
        self.assertEqual(scout["den_number"], self.den.number)
        for field in ("rank", "rank_plural", "rank_key", "rank_badge", "grade"):
            self.assertNotIn(field, scout)
        self.assertEqual(scout["phone_numbers"], [])
        self.assertEqual(scout["emails"], [])

    def test_adult_member_has_no_scout_only_fields(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        parent = self.member(data, self.parent.slug)
        self.assertFalse(parent["is_scout"])
        self.assertIsNone(parent["den_number"])
        for field in ("rank", "rank_plural", "rank_key", "rank_badge", "grade"):
            self.assertNotIn(field, parent)

    def test_family_members_share_a_family_slug(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        parent = self.member(data, self.parent.slug)
        scout = self.member(data, self.scout.slug)
        self.assertIsNotNone(parent["family_slug"])
        self.assertEqual(parent["family_slug"], scout["family_slug"])

    def test_unpublished_email_is_hidden(self):
        self.parent.is_published = False
        self.parent.save()
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(self.member(data, self.parent.slug)["emails"], [])

    def test_unpublished_phone_number_is_hidden(self):
        PhoneNumber.objects.create(number="+15105551234", member=self.parent, published=False)
        PhoneNumber.objects.create(number="+15105554321", member=self.parent, published=True)
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(len(self.member(data, self.parent.slug)["phone_numbers"]), 1)

    def test_contributor_with_no_cubs_is_active_and_linkable(self):
        contributor = AdultFactory(family=FamilyFactory(), role=Adult.CONTRIBUTOR)
        self.client.force_login(self.parent)
        data = self.get_directory()
        entry = self.member(data, contributor.slug)
        self.assertTrue(entry["active"])
        self.assertTrue(entry["linkable"])

    def test_inactive_sibling_is_listed_but_not_linkable(self):
        sibling = ScoutFactory(family=self.family, status=Scout.INACTIVE)
        self.client.force_login(self.parent)
        data = self.get_directory()
        entry = self.member(data, sibling.slug)
        self.assertFalse(entry["active"])
        self.assertFalse(entry["linkable"])

    def test_stranger_outside_any_family_is_absent(self):
        stranger = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)  # no active cubs
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertFalse(any(m["slug"] == stranger.slug for m in data["members"]))

    def test_ordinary_parent_has_no_leadership_title(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIsNone(self.member(data, self.parent.slug)["title"])

    def test_title_comes_from_the_position(self):
        CommitteeMember.objects.create(
            committee=Committee.objects.get(slug="wolf-den"),
            member=self.parent,
            den=self.den,
            year=self.pack_year,
            position=CommitteeMember.Position.DEN_LEADER,
        )
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(self.member(data, self.parent.slug)["title"], "Den Leader")

    def test_the_most_senior_title_wins(self):
        CommitteeMember.objects.create(
            committee=Committee.objects.get(slug="wolf-den"),
            member=self.parent,
            den=self.den,
            year=self.pack_year,
            position=CommitteeMember.Position.DEN_LEADER,
        )
        CommitteeMember.objects.create(
            committee=Committee.objects.create(name="Akela", slug="akela", leadership=True),
            member=self.parent,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertEqual(self.member(data, self.parent.slug)["title"], "Akela")

    def test_prior_years_title_is_not_carried_forward(self):
        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee, member=self.parent, year=last_year, position=CommitteeMember.Position.AKELA
        )
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIsNone(self.member(data, self.parent.slug)["title"])

    def test_user_avatar_is_null_without_a_photo(self):
        self.client.force_login(self.parent)
        data = self.get_directory()
        self.assertIn("avatar", self.member(data, self.parent.slug))
        self.assertIsNone(self.member(data, self.parent.slug)["avatar"])

    def test_user_avatar_is_the_signed_in_members_headshot(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.parent.photo = photo_upload()
            self.parent.save()
            self.client.force_login(self.parent)
            data = self.get_directory()
            avatar = self.member(data, self.parent.slug)["avatar"]
            self.assertIsNotNone(avatar)
            self.assertIn("headshot", avatar)

    def test_an_unreadable_photo_does_not_500_the_whole_directory(self):
        # A photo record can outlive its file on disk (e.g. media not synced
        # alongside a copied database) or point at something that isn't
        # actually an image; either way this shouldn't break the directory
        # for everyone else — just this member's avatar.
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.parent.photo = SimpleUploadedFile("broken.jpg", b"not an image", content_type="image/jpeg")
            self.parent.save()
            self.client.force_login(self.parent)
            response = self.client.get(reverse("mobile:api-directory"))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsNone(self.member(data, self.parent.slug)["avatar"])


class DirectoryDensAPITestCase(MobileDirectoryTestCase):
    def get_dens(self):
        self.client.force_login(self.parent)
        return self.get_directory()["dens"]

    def get_directory(self):
        return self.client.get(reverse("mobile:api-directory")).json()

    def find_den(self, dens, number):
        return next(d for d in dens if d["number"] == number)

    def test_returns_roster_and_leaders(self):
        dens = self.get_dens()
        den = self.find_den(dens, self.den.number)
        self.assertEqual(den["rank"], "Wolf")
        self.assertEqual(len(den["roster"]), 1)
        self.assertEqual(den["roster"][0], self.scout.slug)
        self.assertEqual(len(den["leaders"]), 1)
        self.assertEqual(den["leaders"][0]["slug"], self.leader.slug)

    def test_den_leader_leads_over_assistants(self):
        committee = Committee.objects.get(slug="wolf-den")
        assistant = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=assistant,
            den=self.den,
            year=self.pack_year,
            position=CommitteeMember.Position.ASSISTANT_AKELA,
        )
        den = self.find_den(self.get_dens(), self.den.number)
        self.assertEqual(len(den["leaders"]), 2)
        self.assertEqual(den["leaders"][0]["name"], self.leader.get_full_name())
        self.assertEqual(den["leaders"][0]["position"], "Den Leader")
        self.assertEqual(den["leaders"][1]["position"], "Assistant Akela")

    def test_prior_year_leaders_are_excluded(self):
        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        committee = Committee.objects.get(slug="wolf-den")
        former = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=former,
            den=self.den,
            year=last_year,
            position=CommitteeMember.Position.DEN_LEADER,
        )
        den = self.find_den(self.get_dens(), self.den.number)
        self.assertEqual(len(den["leaders"]), 1)
        self.assertNotIn(former.slug, [leader["slug"] for leader in den["leaders"]])

    def test_roster_is_sorted_by_the_name_it_displays(self):
        for first_name, last_name, nickname in [
            ("Zach", "Adams", "Andy"),
            ("Ava", "Zimmer", ""),
            ("Miles", "Nolan", ""),
        ]:
            cub = ScoutFactory(
                family=FamilyFactory(),
                status=Scout.ACTIVE,
                first_name=first_name,
                last_name=last_name,
                nickname=nickname,
            )
            Membership.objects.create(scout=cub, den=self.den, year_assigned=self.pack_year)
        den = self.find_den(self.get_dens(), self.den.number)
        members = {m["slug"]: m for m in self.get_directory()["members"]}
        names = [members[slug]["short_name"] for slug in den["roster"]]
        self.assertEqual(names, sorted(names, key=str.lower))
        self.assertIn("Andy", names)
        self.assertNotIn("Zach", names)

    def test_dens_without_a_current_roster_are_excluded(self):
        empty_rank = Rank.objects.create(rank=Rank.RankChoices.BEAR)
        empty_den = DenFactory(rank=empty_rank)
        dens = self.get_dens()
        self.assertNotIn(empty_den.number, [d["number"] for d in dens])


class DirectoryCommitteesAPITestCase(MobileDirectoryTestCase):
    def get_directory(self):
        self.client.force_login(self.parent)
        return self.client.get(reverse("mobile:api-directory")).json()

    def committee(self, data, slug):
        return next(c for c in data["committees"] if c["slug"] == slug)

    def flat_membership(self, committee_data, year_key):
        """Every membership entry for a year, regardless of position."""
        return [entry for entries in committee_data["membership"][year_key].values() for entry in entries]

    def test_lists_committees_with_a_current_roster(self):
        data = self.get_directory()
        self.assertTrue(any(c["slug"] == "wolf-den" for c in data["committees"]))

    def test_leadership_flag_is_reported(self):
        akela_committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=akela_committee,
            member=AdultFactory(family=FamilyFactory()),
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        data = self.get_directory()
        self.assertTrue(self.committee(data, "akela")["leadership"])
        self.assertFalse(self.committee(data, "wolf-den")["leadership"])

    def test_committee_without_a_recent_roster_is_excluded(self):
        old_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 6)
        retired = Committee.objects.create(name="Popcorn", slug="popcorn")
        CommitteeMember.objects.create(
            committee=retired,
            member=AdultFactory(family=FamilyFactory()),
            year=old_year,
        )
        data = self.get_directory()
        self.assertNotIn("popcorn", [c["slug"] for c in data["committees"]])

    def test_committee_membership_is_grouped_by_position_in_server_order(self):
        committee = Committee.objects.get(slug="wolf-den")
        akela = AdultFactory(family=FamilyFactory(), first_name="Aaron", last_name="Akela")
        CommitteeMember.objects.create(
            committee=committee,
            member=akela,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        data = self.get_directory()
        year_key = str(self.pack_year.year)
        by_position = self.committee(data, "wolf-den")["membership"][year_key]
        # self.leader is the den's DEN_LEADER (position 4); Akela is position
        # 5 — lower position numbers sort first, so "Den Leader" is the first
        # key and "Akela" the second, each holding its own flat roster.
        self.assertEqual(list(by_position.keys()), ["Den Leader", "Akela"])
        self.assertEqual([m["slug"] for m in by_position["Den Leader"]], [self.leader.slug])
        self.assertEqual([m["slug"] for m in by_position["Akela"]], [akela.slug])

    def test_a_linked_committee_assignment_resolves_by_slug(self):
        # Use self.parent (already in the directory, part of an active
        # family) so linked is expected to be True.
        committee = Committee.objects.get(slug="wolf-den")
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        data = self.get_directory()
        year_key = str(self.pack_year.year)
        entry = next(
            row
            for row in self.flat_membership(self.committee(data, "wolf-den"), year_key)
            if row["slug"] == self.parent.slug
        )
        self.assertTrue(entry["linked"])

    def test_akela_outside_the_directory_is_named_but_not_linked(self):
        stranger = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)  # no active cubs
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=stranger,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        data = self.get_directory()
        year_key = str(self.pack_year.year)
        entry = self.committee(data, "akela")["membership"][year_key]["Akela"][0]
        self.assertEqual(entry["slug"], stranger.slug)
        self.assertEqual(entry["name"], stranger.get_full_name())
        self.assertFalse(entry["linked"])

    def test_years_are_capped_to_the_last_five(self):
        committee = Committee.objects.get(slug="wolf-den")
        for offset in range(1, 7):
            year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - offset)
            CommitteeMember.objects.create(
                committee=committee,
                member=AdultFactory(family=FamilyFactory()),
                year=year,
            )
        data = self.get_directory()
        years = self.committee(data, "wolf-den")["years"]
        self.assertEqual(len(years), 5)
        self.assertEqual(years, sorted(years, reverse=True))
        self.assertNotIn(self.pack_year.year - 6, years)
        self.assertNotIn(str(self.pack_year.year - 6), self.committee(data, "wolf-den")["membership"])

    def test_unknown_committee_is_absent(self):
        data = self.get_directory()
        self.assertNotIn("does-not-exist", [c["slug"] for c in data["committees"]])


class ApiPermissionTestCase(MobileDirectoryTestCase):
    """The API views enforce the same access rule as the shell (IsActiveMemberOrContributor)."""

    ENDPOINTS = ("mobile:api-directory", "mobile:api-event")

    def test_inactive_parent_is_forbidden(self):
        inactive = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)  # no active cubs
        self.client.force_login(inactive)
        for name in self.ENDPOINTS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, msg=name)

    def test_contributor_with_no_cubs_is_allowed(self):
        contributor = AdultFactory(family=FamilyFactory(), role=Adult.CONTRIBUTOR)
        self.client.force_login(contributor)
        for name in self.ENDPOINTS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, msg=name)
