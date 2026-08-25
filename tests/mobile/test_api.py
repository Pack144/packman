import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image

from packman.address_book.models import PhoneNumber
from packman.calendars.models import Category, Event
from packman.membership.models import Scout

from .base import MobileDirectoryTestCase


def photo_upload(name="headshot.png"):
    """A small real image, so easy_thumbnails has something to resize."""
    buffer = BytesIO()
    Image.new("RGB", (200, 200), "navy").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class HomeAPITestCase(MobileDirectoryTestCase):
    def test_anonymous_is_forbidden(self):
        response = self.client.get(reverse("mobile:api-home"))
        self.assertEqual(response.status_code, 403)

    def test_returns_the_signed_in_users_family(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-home"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data["pack"])
        self.assertEqual(data["family"]["name"], self.family.name)
        self.assertEqual(len(data["family"]["children"]), 1)
        self.assertEqual(data["family"]["children"][0]["name"], self.scout.short_name)
        self.assertEqual(data["family"]["children"][0]["den_label"], f"Den {self.den.number} · Wolves")

    def test_user_avatar_is_null_without_a_photo(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-home")).json()
        # The key is always present; the app falls back to initials when null.
        self.assertIn("avatar", data["user"])
        self.assertIsNone(data["user"]["avatar"])

    def test_user_avatar_is_the_signed_in_members_headshot(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.parent.photo = photo_upload()
            self.parent.save()
            self.client.force_login(self.parent)
            data = self.client.get(reverse("mobile:api-home")).json()
            self.assertIsNotNone(data["user"]["avatar"])
            self.assertIn("headshot", data["user"]["avatar"])

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
        data = self.client.get(reverse("mobile:api-home")).json()
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
        data = self.client.get(reverse("mobile:api-home")).json()
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
        data = self.client.get(reverse("mobile:api-home")).json()
        self.assertIsNone(data["event"])

    def test_no_event_returns_null(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-home")).json()
        self.assertIsNone(data["event"])

    def test_no_akela_assigned_returns_null(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-home")).json()
        self.assertIsNone(data["akela"])

    def test_returns_the_current_akela(self):
        from packman.committees.models import Committee, CommitteeMember

        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        akela = self.client.get(reverse("mobile:api-home")).json()["akela"]
        self.assertEqual(akela["slug"], self.parent.slug)
        self.assertEqual(akela["name"], self.parent.get_full_name())
        self.assertEqual(akela["title"], "Akela")
        self.assertTrue(akela["linked"])

    def test_an_akela_outside_the_directory_is_named_but_not_linked(self):
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory
        from packman.membership.models import Adult

        # No active cubs and not a contributor, so MemberDetailView would 404.
        stranger = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=stranger,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        akela = self.client.get(reverse("mobile:api-home")).json()["akela"]
        self.assertEqual(akela["slug"], stranger.slug)
        self.assertFalse(akela["linked"])

    def test_a_den_leader_is_not_mistaken_for_the_akela(self):
        self.client.force_login(self.parent)
        # The fixture's only committee assignment is a Den Leader.
        self.assertIsNone(self.client.get(reverse("mobile:api-home")).json()["akela"])


class MyDensAPITestCase(MobileDirectoryTestCase):
    def test_returns_the_dens_for_the_users_own_cubs(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-dens-mine"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["cub_count"], 1)
        dens = data["dens"]
        self.assertEqual(len(dens), 1)
        self.assertEqual(dens[0]["number"], self.den.number)
        self.assertEqual(dens[0]["rank"], "Wolf")
        self.assertEqual(dens[0]["rank_key"], "wolf")
        self.assertEqual(dens[0]["grade"], "2nd Grade")
        self.assertEqual(dens[0]["my_cub"], self.scout.short_name)
        self.assertEqual(len(dens[0]["roster"]), 1)
        self.assertEqual(dens[0]["roster"][0]["scout"]["name"], self.scout.short_name)
        self.assertEqual(len(dens[0]["leaders"]), 1)
        self.assertEqual(dens[0]["leaders"][0]["name"], self.leader.get_full_name())
        self.assertEqual(dens[0]["leaders"][0]["email"], self.leader.email)

    def test_maps_each_den_to_the_right_cub_across_multiple_dens(self):
        from packman.dens.factories import DenFactory
        from packman.dens.models import Membership, Rank
        from packman.membership.factories import ScoutFactory
        from packman.membership.models import Scout

        tiger_rank = Rank.objects.create(rank=Rank.RankChoices.TIGER)
        second_den = DenFactory(rank=tiger_rank)
        sibling = ScoutFactory(family=self.family, status=Scout.ACTIVE)
        Membership.objects.create(scout=sibling, den=second_den, year_assigned=self.pack_year)

        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-dens-mine")).json()
        self.assertEqual(data["cub_count"], 2)
        # Dens come back ordered by den number.
        self.assertEqual([d["number"] for d in data["dens"]], sorted([self.den.number, second_den.number]))
        by_number = {d["number"]: d for d in data["dens"]}
        self.assertEqual(by_number[self.den.number]["my_cub"], self.scout.short_name)
        self.assertEqual(by_number[second_den.number]["my_cub"], sibling.short_name)


class DenListAPITestCase(MobileDirectoryTestCase):
    def test_flags_the_users_own_den(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-dens"))
        self.assertEqual(response.status_code, 200)
        dens = response.json()["dens"]
        mine = next(d for d in dens if d["number"] == self.den.number)
        self.assertTrue(mine["is_mine"])
        self.assertEqual(mine["my_cub"], self.scout.short_name)


class DenDetailAPITestCase(MobileDirectoryTestCase):
    def test_returns_roster_and_leaders(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-den-detail", args=[self.den.number]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["number"], self.den.number)
        self.assertEqual(len(data["roster"]), 1)
        self.assertEqual(len(data["leaders"]), 1)

    def test_den_leader_leads_over_assistants(self):
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        committee = Committee.objects.get(slug="wolf-den")
        assistant = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=assistant,
            den=self.den,
            year=self.pack_year,
            position=CommitteeMember.Position.ASSISTANT_AKELA,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-den-detail", args=[self.den.number])).json()
        self.assertEqual(len(data["leaders"]), 2)
        # The Den Leader is listed first, whatever other roles support the den.
        self.assertEqual(data["leaders"][0]["name"], self.leader.get_full_name())
        self.assertEqual(data["leaders"][0]["position"], "Den Leader")
        self.assertEqual(data["leaders"][1]["position"], "Assistant Akela")

    def test_prior_year_leaders_are_excluded(self):
        from packman.calendars.models import PackYear
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

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
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-den-detail", args=[self.den.number])).json()
        self.assertEqual(len(data["leaders"]), 1)
        self.assertNotIn(former.get_full_name(), [leader["name"] for leader in data["leaders"]])

    def test_roster_is_sorted_by_the_name_it_displays(self):
        from packman.dens.models import Membership
        from packman.membership.factories import FamilyFactory, ScoutFactory

        # Last names run counter to first names, so a roster still ordered by
        # surname would come back reversed. Zach goes by "Andy": he sorts under
        # the nickname the row actually shows, not under his first name.
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
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-den-detail", args=[self.den.number])).json()
        names = [entry["scout"]["name"] for entry in data["roster"]]
        self.assertEqual(names, sorted(names, key=str.lower))
        self.assertIn("Andy", names)
        self.assertNotIn("Zach", names)

    def test_unknown_den_is_404(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-den-detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class SearchAPITestCase(MobileDirectoryTestCase):
    def test_finds_the_cub_by_name(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-search"), {"q": self.scout.first_name})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertTrue(any(r["slug"] == self.scout.slug and r["type"] == "cub" for r in results))

    def test_empty_query_returns_no_results(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-search"), {"q": ""})
        self.assertEqual(response.json()["results"], [])

    def test_cub_filter_returns_only_cubs(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-search"), {"q": self.scout.first_name, "type": "cub"}).json()
        self.assertEqual(data["parents"], [])
        self.assertTrue(any(r["slug"] == self.scout.slug for r in data["cubs"]))
        self.assertTrue(all(r["type"] == "cub" for r in data["results"]))

    def test_parent_filter_returns_only_parents_with_cub_subtitle(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-search"), {"q": self.parent.last_name, "type": "parent"}).json()
        self.assertEqual(data["cubs"], [])
        result = next(r for r in data["parents"] if r["slug"] == self.parent.slug)
        self.assertEqual(result["type"], "parent")
        self.assertEqual(result["subtitle"], f"Parent of {self.scout.short_name}")

    def test_contributor_result_uses_role_as_subtitle(self):
        from packman.membership.factories import AdultFactory, FamilyFactory
        from packman.membership.models import Adult

        contributor = AdultFactory(family=FamilyFactory(), role=Adult.CONTRIBUTOR)
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-search"), {"q": contributor.last_name, "type": "parent"}).json()
        result = next(r for r in data["parents"] if r["slug"] == contributor.slug)
        self.assertEqual(result["subtitle"], contributor.get_role_display())

    def test_flat_results_combine_grouped_cubs_and_parents(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-search"), {"q": self.parent.last_name}).json()
        grouped = {r["slug"] for r in data["cubs"] + data["parents"]}
        self.assertEqual(grouped, {r["slug"] for r in data["results"]})


class MemberDetailAPITestCase(MobileDirectoryTestCase):
    def test_scout_profile_lists_parent(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[self.scout.slug]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_scout"])
        self.assertEqual(data["den"], f"Den {self.den.number} · Wolves")
        self.assertEqual(data["den_number"], self.den.number)
        self.assertEqual(data["rank"], "Wolf")
        self.assertEqual(data["rank_plural"], "Wolves")
        self.assertEqual(data["rank_key"], "wolf")
        # The profile labels the grade the way the den screens do — and not as
        # the "2Nd Grade" that title-casing the school grade used to produce.
        self.assertEqual(data["grade"], "2nd Grade")
        self.assertIn(self.parent.slug, [f["slug"] for f in data["family"]])
        parent_entry = next(f for f in data["family"] if f["slug"] == self.parent.slug)
        self.assertTrue(parent_entry["active"])

    def test_active_sibling_is_linkable(self):
        from packman.membership.factories import ScoutFactory

        sibling = ScoutFactory(family=self.family, status=Scout.ACTIVE)
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.scout.slug])).json()
        family = {f["slug"]: f for f in data["family"]}
        self.assertTrue(family[sibling.slug]["active"])
        self.assertNotIn("No longer active", family[sibling.slug]["relation"])

    def test_inactive_sibling_is_listed_but_not_linkable(self):
        from packman.membership.factories import ScoutFactory

        sibling = ScoutFactory(family=self.family, status=Scout.INACTIVE)
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.scout.slug])).json()
        family = {f["slug"]: f for f in data["family"]}

        # Still shown — they're part of the family — but flagged so the
        # frontend won't link to a profile that's outside visibility scope.
        self.assertIn(sibling.slug, family)
        self.assertFalse(family[sibling.slug]["active"])
        self.assertIn("No longer active", family[sibling.slug]["relation"])

        # And that profile really is out of scope, confirming the flag matches
        # what would happen if the frontend linked there anyway.
        response = self.client.get(reverse("mobile:api-member-detail", args=[sibling.slug]))
        self.assertEqual(response.status_code, 404)

    def test_adult_profile_lists_partner_and_cub_children(self):
        from packman.membership.factories import AdultFactory
        from packman.membership.models import Adult

        partner = AdultFactory(family=self.family, role=Adult.PARENT)
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertFalse(data["is_scout"])

        # An adult has none of the cub-only den/rank presentation fields.
        self.assertIsNone(data["den_number"])
        self.assertIsNone(data["rank_plural"])
        self.assertIsNone(data["grade"])

        family = {member["slug"]: member for member in data["family"]}

        # The partner appears with their role as the relation and carries no rank.
        self.assertIn(partner.slug, family)
        self.assertEqual(family[partner.slug]["relation"], partner.get_role_display())
        self.assertIsNone(family[partner.slug]["rank"])
        self.assertIsNone(family[partner.slug]["rank_key"])
        self.assertTrue(family[partner.slug]["active"])

        # The cub child appears with a "Cub · Den …" relation and their rank.
        self.assertIn(self.scout.slug, family)
        self.assertTrue(family[self.scout.slug]["active"])
        self.assertEqual(family[self.scout.slug]["relation"], f"Cub · Den {self.den.number} · Wolves")
        self.assertEqual(family[self.scout.slug]["rank"], "Wolf")
        self.assertEqual(family[self.scout.slug]["rank_key"], "wolf")

    def test_unpublished_email_is_hidden(self):
        self.parent.is_published = False
        self.parent.save()
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug]))
        self.assertEqual(response.json()["emails"], [])

    def test_unpublished_phone_number_is_hidden(self):
        PhoneNumber.objects.create(number="+15105551234", member=self.parent, published=False)
        PhoneNumber.objects.create(number="+15105554321", member=self.parent, published=True)
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug]))
        phone_numbers = response.json()["phone_numbers"]
        self.assertEqual(len(phone_numbers), 1)

    def test_scout_has_no_leadership_title(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.scout.slug])).json()
        self.assertIsNone(data["title"])

    def test_ordinary_parent_has_no_leadership_title(self):
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertIsNone(data["title"])

    def test_title_comes_from_the_position(self):
        from packman.committees.models import Committee, CommitteeMember

        CommitteeMember.objects.create(
            committee=Committee.objects.get(slug="wolf-den"),
            member=self.parent,
            den=self.den,
            year=self.pack_year,
            position=CommitteeMember.Position.DEN_LEADER,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertEqual(data["title"], "Den Leader")

    def test_title_falls_back_to_the_committee_name(self):
        from packman.committees.models import Committee, CommitteeMember

        # A Pack that records the title in the committee name and leaves every
        # member at the default "Member" position.
        committee = Committee.objects.create(name="Assistant Akelas", slug="assistant-akelas", leadership=True)
        CommitteeMember.objects.create(committee=committee, member=self.parent, year=self.pack_year)
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertEqual(data["title"], "Assistant Akela")

    def test_a_non_leadership_committee_grants_no_title(self):
        from packman.committees.models import Committee, CommitteeMember

        committee = Committee.objects.create(name="Advancements", slug="advancements")
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=self.pack_year,
            position=CommitteeMember.Position.CHAIR,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertIsNone(data["title"])

    def test_the_most_senior_title_wins(self):
        from packman.committees.models import Committee, CommitteeMember

        # Leading a den and serving as Akela reads as the more senior of the two,
        # even though ASSISTANT_AKELA/AKELA sort above DEN_LEADER numerically.
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
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertEqual(data["title"], "Akela")

    def test_prior_years_title_is_not_carried_forward(self):
        from packman.calendars.models import PackYear
        from packman.committees.models import Committee, CommitteeMember

        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=committee,
            member=self.parent,
            year=last_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug])).json()
        self.assertIsNone(data["title"])

    def test_member_outside_visibility_scope_is_404(self):
        from packman.membership.factories import AdultFactory, FamilyFactory
        from packman.membership.models import Adult

        stranger = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)  # no active scouts
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[stranger.slug]))
        self.assertEqual(response.status_code, 404)


class CommitteeListAPITestCase(MobileDirectoryTestCase):
    def test_lists_committees(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-committees"))
        self.assertEqual(response.status_code, 200)
        committees = response.json()["committees"]
        self.assertTrue(any(c["slug"] == "wolf-den" for c in committees))

    def test_leadership_flag_is_reported(self):
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        akela_committee = Committee.objects.create(name="Akela", slug="akela", leadership=True)
        CommitteeMember.objects.create(
            committee=akela_committee,
            member=AdultFactory(family=FamilyFactory()),
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-committees")).json()
        akela = next(c for c in data["committees"] if c["slug"] == "akela")
        self.assertTrue(akela["leadership"])
        wolf_den = next(c for c in data["committees"] if c["slug"] == "wolf-den")
        self.assertFalse(wolf_den["leadership"])

    def test_committee_without_a_current_roster_is_excluded(self):
        from packman.calendars.models import PackYear
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        retired = Committee.objects.create(name="Popcorn", slug="popcorn")
        CommitteeMember.objects.create(
            committee=retired,
            member=AdultFactory(family=FamilyFactory()),
            year=last_year,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-committees")).json()
        self.assertNotIn("popcorn", [c["slug"] for c in data["committees"]])

    def test_committee_is_listed_once_per_year_however_many_members(self):
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        committee = Committee.objects.get(slug="wolf-den")
        for _ in range(2):
            CommitteeMember.objects.create(
                committee=committee,
                member=AdultFactory(family=FamilyFactory()),
                year=self.pack_year,
            )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-committees")).json()
        slugs = [c["slug"] for c in data["committees"]]
        self.assertEqual(slugs.count("wolf-den"), 1)


class CommitteeDetailAPITestCase(MobileDirectoryTestCase):
    def test_returns_current_years_roster(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-committee-detail", args=["wolf-den"]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Wolf Den")
        self.assertEqual(data["year"], self.pack_year.year)
        self.assertEqual(len(data["members"]), 1)
        self.assertEqual(data["members"][0]["name"], self.leader.get_full_name())
        self.assertEqual(data["akelas"], [])

    def test_akelas_are_separated_from_members(self):
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        committee = Committee.objects.get(slug="wolf-den")
        akela = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=akela,
            year=self.pack_year,
            position=CommitteeMember.Position.AKELA,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-committee-detail", args=["wolf-den"])).json()
        self.assertEqual(len(data["akelas"]), 1)
        self.assertEqual(data["akelas"][0]["name"], akela.get_full_name())
        self.assertEqual(len(data["members"]), 1)

    def test_prior_year_members_are_excluded_by_default(self):
        from packman.calendars.models import PackYear
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        committee = Committee.objects.get(slug="wolf-den")
        former = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=former,
            year=last_year,
            position=CommitteeMember.Position.MEMBER,
        )
        self.client.force_login(self.parent)
        data = self.client.get(reverse("mobile:api-committee-detail", args=["wolf-den"])).json()
        self.assertNotIn(former.get_full_name(), [m["name"] for m in data["members"]])
        # ...but it's still offered as a year to switch to.
        self.assertIn(last_year.year, [y["year"] for y in data["years"]])

    def test_can_request_a_prior_year_explicitly(self):
        from packman.calendars.models import PackYear
        from packman.committees.models import Committee, CommitteeMember
        from packman.membership.factories import AdultFactory, FamilyFactory

        last_year, _ = PackYear.objects.get_or_create(year=self.pack_year.year - 1)
        committee = Committee.objects.get(slug="wolf-den")
        former = AdultFactory(family=FamilyFactory())
        CommitteeMember.objects.create(
            committee=committee,
            member=former,
            year=last_year,
            position=CommitteeMember.Position.MEMBER,
        )
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-committee-detail", args=["wolf-den"]), {"year": last_year.year})
        data = response.json()
        self.assertEqual(data["year"], last_year.year)
        self.assertEqual([m["name"] for m in data["members"]], [former.get_full_name()])

    def test_unknown_committee_is_404(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-committee-detail", args=["does-not-exist"]))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_is_forbidden(self):
        response = self.client.get(reverse("mobile:api-committee-detail", args=["wolf-den"]))
        self.assertEqual(response.status_code, 403)


class ApiPermissionTestCase(MobileDirectoryTestCase):
    """The API views enforce the same access rule as the shell (IsActiveMemberOrContributor)."""

    ENDPOINTS = (
        "mobile:api-home",
        "mobile:api-dens-mine",
        "mobile:api-dens",
        "mobile:api-search",
        "mobile:api-committees",
    )

    def test_inactive_parent_is_forbidden(self):
        from packman.membership.factories import AdultFactory, FamilyFactory
        from packman.membership.models import Adult

        inactive = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)  # no active cubs
        self.client.force_login(inactive)
        for name in self.ENDPOINTS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, msg=name)

    def test_contributor_with_no_cubs_is_allowed(self):
        from packman.membership.factories import AdultFactory, FamilyFactory
        from packman.membership.models import Adult

        contributor = AdultFactory(family=FamilyFactory(), role=Adult.CONTRIBUTOR)
        self.client.force_login(contributor)
        for name in self.ENDPOINTS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, msg=name)
