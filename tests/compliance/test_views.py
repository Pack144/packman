import datetime
import re
from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.committees.models import Committee, CommitteeMember
from packman.compliance.factories import (
    AdultRequirementFactory,
    CubRequirementFactory,
    FamilyRequirementFactory,
    RequirementRecordFactory,
)
from packman.compliance.models import Requirement, RequirementRecord
from packman.compliance.scouting_membership import Standing
from packman.dens.factories import MembershipFactory
from packman.membership.factories import (
    ActiveScoutFactory,
    AdultFactory,
    CompleteFamilyFactory,
    FamilyFactory,
    ScoutFactory,
)
from packman.membership.models import Adult, Family
from packman.membership.models import Scout as ActiveScout


def grant_leadership(adult, year, *codenames):
    """
    Grant permissions the way the site really does: through a committee.

    CommitteePermissionsBackend resolves has_perm() from committee membership,
    so going through user_permissions would not exercise the real path.
    """
    committee = Committee.objects.create(name="Membership", slug=f"membership-{adult.pk}")
    committee.permissions.set(Permission.objects.filter(codename__in=codenames))
    CommitteeMember.objects.create(committee=committee, member=adult, year=year)
    return committee


class ComplianceViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.family = CompleteFamilyFactory(adults=1, active_children=1)
        cls.parent = cls.family.adults.first()
        cls.parent.set_password("devpassword123")  # nosec B106
        cls.parent.save()

        cls.leader_family = CompleteFamilyFactory(adults=1, active_children=1)
        cls.leader = cls.leader_family.adults.first()
        cls.leader.set_password("devpassword123")  # nosec B106
        cls.leader.save()
        grant_leadership(cls.leader, cls.year, "view_all_records", "manage_records")

    def setUp(self):
        cache.clear()

    def login(self, adult):
        self.client.force_login(adult)

    def badge_class_for(self, response, label):
        """
        The Bootstrap colour class on the badge carrying `label`, or None.

        Colour is the whole point of these badges - it is what a parent reads
        before the words - so the tests have to be able to see it, not just the
        text beside it.
        """
        pattern = r'<span class="badge ([\w-]+)"[^>]*>\s*<i[^>]*></i>\s*' + re.escape(label)
        match = re.search(pattern, response.content.decode())
        return match[1] if match else None


class DashboardAccessTestCase(ComplianceViewTestCase):
    url_name = "compliance:dashboard"

    def test_anonymous_is_redirected(self):
        response = self.client.get(reverse(self.url_name))

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_plain_parent_is_forbidden(self):
        self.login(self.parent)

        response = self.client.get(reverse(self.url_name))

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_leadership_may_view(self):
        self.login(self.leader)

        response = self.client.get(reverse(self.url_name))

        self.assertEqual(response.status_code, HTTPStatus.OK)


class RosterAccessTestCase(ComplianceViewTestCase):
    def url(self):
        return reverse("compliance:roster", kwargs={"slug": "roster-access"})

    def setUp(self):
        super().setUp()
        CubRequirementFactory(slug="roster-access")

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url()).status_code, HTTPStatus.FOUND)

    def test_plain_parent_is_forbidden(self):
        self.login(self.parent)

        self.assertEqual(self.client.get(self.url()).status_code, HTTPStatus.FORBIDDEN)

    def test_leadership_may_view(self):
        self.login(self.leader)

        self.assertEqual(self.client.get(self.url()).status_code, HTTPStatus.OK)


class FamilyViewAccessTestCase(ComplianceViewTestCase):
    def url(self, family):
        return reverse("compliance:family_detail", kwargs={"pk": family.pk})

    def test_a_parent_may_see_their_own_family(self):
        self.login(self.parent)

        self.assertEqual(self.client.get(self.url(self.family)).status_code, HTTPStatus.OK)

    def test_a_parent_may_not_see_another_family(self):
        self.login(self.parent)

        self.assertEqual(self.client.get(self.url(self.leader_family)).status_code, HTTPStatus.FORBIDDEN)

    def test_leadership_may_see_any_family(self):
        self.login(self.leader)

        self.assertEqual(self.client.get(self.url(self.family)).status_code, HTTPStatus.OK)

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url(self.family)).status_code, HTTPStatus.FOUND)


class MyFamilyViewTestCase(ComplianceViewTestCase):
    def test_shows_the_signed_in_members_family(self):
        self.login(self.parent)

        response = self.client.get(reverse("compliance:my_family"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["family"], self.family)

    def test_member_without_a_family_gets_an_empty_state(self):
        """
        A Friend of the Pack passes the member-area gate on their role but has
        no family, so the view has to cope with get_object() returning None.
        """
        contributor = AdultFactory(family=None, role=Adult.CONTRIBUTOR)
        self.login(contributor)

        response = self.client.get(reverse("compliance:my_family"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(response.context["family"])
        self.assertEqual(response.context["groups"], [])


class MyFamilyMembershipTestCase(ComplianceViewTestCase):
    """The Scouting America registration row and footer on each person's card."""

    def setUp(self):
        super().setUp()
        self.login(self.parent)
        self.cub = self.family.children.first()

    def get_page(self):
        response = self.client.get(reverse("compliance:my_family"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response

    def register(self, expires_on, membership_id="137042891"):
        self.cub.scouting_membership_id = membership_id
        self.cub.scouting_membership_expires_on = expires_on
        self.cub.save()

    def membership_of(self, response, subject):
        return {group["subject"]: group["membership"] for group in response.context["groups"]}[subject]

    def group_of(self, response, subject):
        return {group["subject"]: group for group in response.context["groups"]}[subject]

    def test_a_registration_lapsing_within_sixty_days_reads_as_expiring_soon(self):
        self.register(timezone.localdate() + datetime.timedelta(days=30))

        response = self.get_page()

        self.assertEqual(self.membership_of(response, self.cub)["standing"], Standing.EXPIRING_SOON)
        self.assertContains(response, "Expiring Soon")

    def test_a_registration_well_in_the_future_reads_as_current(self):
        self.register(timezone.localdate() + datetime.timedelta(days=200))

        self.assertEqual(self.membership_of(self.get_page(), self.cub)["standing"], Standing.CURRENT)

    def test_a_lapsed_registration_reads_as_expired(self):
        self.register(timezone.localdate() - datetime.timedelta(days=1))

        self.assertEqual(self.membership_of(self.get_page(), self.cub)["standing"], Standing.EXPIRED)

    def test_the_footer_shows_the_expiration_date_but_not_the_membership_id(self):
        """
        The date is what a family can act on. The ID is only needed to transact
        with council at recharter, so it stays on the dashboard and the admin
        rather than on a page every family loads.
        """
        expires_on = timezone.localdate() + datetime.timedelta(days=30)
        self.register(expires_on)

        response = self.get_page()

        self.assertContains(response, "Registration Expires")
        self.assertContains(response, date_format(expires_on, "SHORT_DATE_FORMAT"))
        self.assertNotContains(response, "137042891")

    def test_a_cub_with_nothing_on_file_shows_a_row_but_no_footer(self):
        response = self.get_page()

        self.assertEqual(self.membership_of(response, self.cub)["standing"], Standing.MISSING)
        # The Cub is being asked for one, so the empty row reads as owed.
        self.assertContains(response, "Required", count=1)
        # With nothing recorded there is no expiration footer.
        self.assertNotContains(response, "Registration Expires")

    def test_an_id_with_no_expiration_date_shows_no_footer(self):
        """Half a registration is not one, and there is no date to print."""
        self.cub.scouting_membership_id = "137042891"
        self.cub.save()

        response = self.get_page()

        self.assertEqual(self.membership_of(response, self.cub)["standing"], Standing.MISSING)
        self.assertNotContains(response, "Registration Expires")

    def test_an_active_cub_with_nothing_on_file_is_expected_to_have_one(self):
        response = self.get_page()

        self.assertTrue(self.group_of(response, self.cub)["expected"])

    def test_an_owed_registration_is_amber_not_grey(self):
        """
        Grey is what an unrecorded requirement wears, so an owed registration in
        grey reads as one. Amber matches the "needs attention" alert counting it.
        """
        RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="colour-cub"),
            year=self.year,
            member=self.cub,
        )

        response = self.get_page()

        self.assertEqual(self.badge_class_for(response, "Required"), "text-bg-warning")
        # The requirement beside it stays grey, which is the whole distinction.
        self.assertEqual(self.badge_class_for(response, "Not started"), "text-bg-secondary")

    def test_each_registration_standing_gets_its_own_colour(self):
        for label, expires_on, expected in (
            ("Current", timezone.localdate() + datetime.timedelta(days=200), "text-bg-success"),
            ("Expiring Soon", timezone.localdate() + datetime.timedelta(days=30), "text-bg-warning"),
            ("Expired", timezone.localdate() - datetime.timedelta(days=1), "text-bg-danger"),
        ):
            with self.subTest(label):
                self.register(expires_on)

                self.assertEqual(self.badge_class_for(self.get_page(), label), expected)

    def test_an_adult_carries_no_registration_row(self):
        """
        The pack tracks its Cubs' registrations. Akelas and Den Leaders hold one
        too, but council administers those, so nothing here claims to know.
        """
        response = self.get_page()

        self.assertIsNone(self.membership_of(response, self.parent))
        self.assertNotContains(response, "Not on file")
        # One registration row on the page, and it is the Cub's.
        self.assertContains(response, "Scouting America Registration", count=1)

    def test_the_household_group_carries_no_registration(self):
        requirement = FamilyRequirementFactory(slug="family-conduct")
        requirement.sync_records(year=self.year)

        household = [g for g in self.get_page().context["groups"] if g["subject"] == self.family]

        self.assertEqual([g["membership"] for g in household], [None])

    def test_the_page_does_not_scale_queries_with_family_size(self):
        def count(children):
            # Active Cubs, so the extra children actually get rendered a card.
            while self.family.children.count() < children:
                ActiveScoutFactory(family=self.family)
            cache.clear()
            self.client.get(reverse("compliance:my_family"))
            cache.clear()
            with CaptureQueriesContext(connection) as captured:
                self.client.get(reverse("compliance:my_family"))
            return len(captured.captured_queries)

        self.assertEqual(count(2), count(6))


class FamilyNeedsAttentionTestCase(ComplianceViewTestCase):
    """
    What the banner counts. A Cub the pack is still waiting on a registration
    for is an open item, so the page cannot call itself up to date while one is.
    """

    def setUp(self):
        super().setUp()
        self.login(self.parent)
        self.cub = self.family.children.first()

    def register(self, member, expires_on, membership_id="137042891"):
        member.scouting_membership_id = membership_id
        member.scouting_membership_expires_on = expires_on
        member.save()

    def get_page(self):
        response = self.client.get(reverse("compliance:my_family"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response

    def test_an_active_cub_with_no_registration_needs_attention(self):
        """Nothing on file is an open item, so the page cannot call itself up to date."""
        response = self.get_page()

        self.assertEqual(response.context["registrations_due"], [self.cub])
        self.assertEqual(response.context["needs_attention"], 1)
        self.assertContains(response, "still needs attention")
        self.assertNotContains(response, "Everything is up to date")

    def test_a_registered_cub_leaves_the_family_up_to_date(self):
        self.register(self.cub, timezone.localdate() + datetime.timedelta(days=200))

        response = self.get_page()

        self.assertEqual(response.context["needs_attention"], 0)
        self.assertContains(response, "Everything is up to date")

    def test_an_expiring_or_lapsed_registration_still_needs_attention(self):
        """Anything the card does not badge green is something to act on."""
        for label, expires_on in (
            ("expiring soon", timezone.localdate() + datetime.timedelta(days=30)),
            ("lapsed", timezone.localdate() - datetime.timedelta(days=1)),
        ):
            with self.subTest(label):
                self.register(self.cub, expires_on)

                self.assertEqual(self.get_page().context["registrations_due"], [self.cub])

    def test_an_adult_cannot_add_to_the_count(self):
        """Adults hold no registration here at all, so there is nothing to count."""
        self.register(self.cub, timezone.localdate() + datetime.timedelta(days=200))

        response = self.get_page()

        adult_groups = [g for g in response.context["groups"] if g["subject"] == self.parent]
        self.assertEqual([g["membership"] for g in adult_groups], [None])
        self.assertEqual(response.context["needs_attention"], 0)

    def test_a_cub_who_is_not_active_this_year_is_not_badged_as_owing_one(self):
        """A Cub the pack is not asking for a registration is shown their
        standing as a fact; the badge and the attention count agree."""
        stray = ScoutFactory(family=self.family, status=ActiveScout.ACTIVE)
        RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="attention-stray"),
            year=self.year,
            member=stray,
            status=RequirementRecord.Status.COMPLETE,
        )
        self.register(self.cub, timezone.localdate() + datetime.timedelta(days=200))

        response = self.get_page()

        groups = {group["subject"]: group for group in response.context["groups"]}
        self.assertIn(stray, groups)
        self.assertFalse(groups[stray]["expected"])
        self.assertFalse(groups[stray]["registration_due"])
        self.assertEqual(response.context["needs_attention"], 0)
        self.assertContains(response, "Everything is up to date")
        self.assertNotContains(response, "Required")

    def test_records_and_registrations_are_counted_together(self):
        RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="attention-cub"),
            year=self.year,
            member=self.cub,
        )

        response = self.get_page()

        self.assertEqual(len(response.context["outstanding"]), 1)
        self.assertEqual(response.context["registrations_due"], [self.cub])
        self.assertEqual(response.context["needs_attention"], 2)


class InactiveScoutTestCase(ComplianceViewTestCase):
    """Who gets a card. A sibling who has left the pack is clutter, not news."""

    def setUp(self):
        super().setUp()
        self.login(self.parent)
        self.cub = self.family.children.first()

    def subjects(self):
        response = self.client.get(reverse("compliance:my_family"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.response = response
        return [group["subject"] for group in response.context["groups"]]

    def group_of(self, response, subject):
        return {group["subject"]: group for group in response.context["groups"]}[subject]

    def test_a_scout_who_is_not_active_this_year_gets_no_card(self):
        sibling = ScoutFactory(family=self.family)

        subjects = self.subjects()

        self.assertIn(self.cub, subjects)
        self.assertNotIn(sibling, subjects)
        self.assertNotContains(self.response, str(sibling))

    def test_a_withdrawn_scout_gets_no_card(self):
        sibling = ScoutFactory(family=self.family, status=ActiveScout.WITHDRAWN)
        MembershipFactory(scout=sibling, year_assigned=self.year)

        self.assertNotIn(sibling, self.subjects())

    def test_a_scout_who_left_part_way_through_keeps_their_records_visible(self):
        """Dropping the card would hide records the banner is still counting."""
        sibling = ScoutFactory(family=self.family)
        RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="inactive-left"),
            year=self.year,
            member=sibling,
        )

        subjects = self.subjects()

        self.assertIn(sibling, subjects)
        self.assertEqual(len(self.response.context["outstanding"]), 1)
        # Nobody is asking a Cub who has left to renew a registration.
        self.assertEqual(self.response.context["registrations_due"], [self.cub])
        # So their empty registration stays grey: a fact, not an open item.
        self.assertFalse(self.group_of(self.response, sibling)["expected"])
        self.assertEqual(self.badge_class_for(self.response, "Not on file"), "text-bg-secondary")
        self.assertEqual(self.badge_class_for(self.response, "Required"), "text-bg-warning")


class DashboardContentTestCase(ComplianceViewTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.leader)
        self.requirement = CubRequirementFactory(slug="content-cub")

    def test_rollup_counts_each_state(self):
        scouts = [ActiveScoutFactory() for _ in range(3)]
        RequirementRecordFactory(requirement=self.requirement, year=self.year, member=scouts[0])
        RequirementRecordFactory(
            requirement=self.requirement,
            year=self.year,
            member=scouts[1],
            status=RequirementRecord.Status.COMPLETE,
        )
        RequirementRecordFactory(
            requirement=self.requirement,
            year=self.year,
            member=scouts[2],
            status=RequirementRecord.Status.WAIVED,
        )

        response = self.client.get(reverse("compliance:dashboard"))

        rollup = {r.slug: r for r in response.context["requirements"]}[self.requirement.slug]
        self.assertEqual(rollup.total, 3)
        self.assertEqual(rollup.outstanding, 1)
        self.assertEqual(rollup.complete, 1)
        self.assertEqual(rollup.waived, 1)

    def test_matrix_lists_active_families(self):
        response = self.client.get(reverse("compliance:dashboard"))

        families = {row["family"] for row in response.context["families"]["rows"]}
        self.assertIn(self.family, families)

    def test_filter_narrows_to_families_with_outstanding_items(self):
        dues = FamilyRequirementFactory(slug="content-dues")
        RequirementRecordFactory(requirement=dues, year=self.year, member=None, family=self.family)
        RequirementRecordFactory(
            requirement=dues,
            year=self.year,
            member=None,
            family=self.leader_family,
            status=RequirementRecord.Status.COMPLETE,
        )

        response = self.client.get(reverse("compliance:dashboard"), {"filter": "outstanding"})

        families = [row["family"] for row in response.context["families"]["rows"]]
        self.assertEqual(families, [self.family])

    def test_dashboard_does_not_scale_queries_with_families(self):
        """
        Guards the rollup and matrix against slipping back into a per-family
        query, which is what campaigns' leaderboard does.
        """
        baseline = self.count_dashboard_queries(extra_families=3)
        grown = self.count_dashboard_queries(extra_families=9)

        self.assertEqual(grown, baseline)

    def count_dashboard_queries(self, extra_families):
        while Family.objects.count() < extra_families:
            CompleteFamilyFactory(adults=2, active_children=2)
        self.requirement.sync_records(year=self.year)
        cache.clear()

        with CaptureQueriesContext(connection) as captured:
            self.client.get(reverse("compliance:dashboard"))
        return len(captured.captured_queries)


class RosterContentTestCase(ComplianceViewTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.leader)

    def test_lists_cubs_with_no_record_yet(self):
        """A Cub who joined after the sync still has to appear."""
        requirement = CubRequirementFactory(slug="roster-late")
        ActiveScoutFactory()

        response = self.client.get(reverse("compliance:roster", kwargs={"slug": requirement.slug}))

        rows = response.context["rows"]
        self.assertTrue(rows)
        self.assertTrue(all(row["record"] is None for row in rows))

    def test_pairs_subjects_with_their_records(self):
        requirement = CubRequirementFactory(slug="roster-paired")
        scout = ActiveScoutFactory()
        record = RequirementRecordFactory(requirement=requirement, year=self.year, member=scout)

        response = self.client.get(reverse("compliance:roster", kwargs={"slug": requirement.slug}))

        match = next(row for row in response.context["rows"] if row["subject"].pk == scout.pk)
        self.assertEqual(match["record"], record)

    def test_family_requirement_lists_families(self):
        requirement = FamilyRequirementFactory(slug="roster-families")

        response = self.client.get(reverse("compliance:roster", kwargs={"slug": requirement.slug}))

        self.assertIn(self.family, [row["subject"] for row in response.context["rows"]])

    def test_adult_requirement_lists_adults(self):
        requirement = AdultRequirementFactory(slug="roster-adults")

        response = self.client.get(reverse("compliance:roster", kwargs={"slug": requirement.slug}))

        self.assertIn(self.parent.pk, [row["subject"].pk for row in response.context["rows"]])


class FamilyContentTestCase(ComplianceViewTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.parent)

    def test_groups_records_by_person_and_household(self):
        cub_requirement = CubRequirementFactory(slug="family-cub")
        dues = FamilyRequirementFactory(slug="family-dues")
        scout = self.family.children.first()
        RequirementRecordFactory(requirement=cub_requirement, year=self.year, member=scout)
        RequirementRecordFactory(requirement=dues, year=self.year, member=None, family=self.family)

        response = self.client.get(reverse("compliance:family_detail", kwargs={"pk": self.family.pk}))

        groups = response.context["groups"]
        subjects = [str(group["subject"]) for group in groups]
        self.assertIn(str(scout), subjects)
        self.assertIn(str(self.family), subjects)

    def test_outstanding_lists_only_unsatisfied_records(self):
        requirement = CubRequirementFactory(slug="family-outstanding")
        scout = self.family.children.first()
        RequirementRecordFactory(requirement=requirement, year=self.year, member=scout)

        response = self.client.get(reverse("compliance:family_detail", kwargs={"pk": self.family.pk}))

        self.assertEqual(len(response.context["outstanding"]), 1)

    def test_completed_records_are_not_outstanding(self):
        requirement = CubRequirementFactory(slug="family-satisfied")
        scout = self.family.children.first()
        RequirementRecordFactory(
            requirement=requirement,
            year=self.year,
            member=scout,
            status=RequirementRecord.Status.COMPLETE,
        )

        response = self.client.get(reverse("compliance:family_detail", kwargs={"pk": self.family.pk}))

        self.assertEqual(response.context["outstanding"], [])


class YearSwitcherTestCase(ComplianceViewTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.leader)

    def test_available_years_carry_their_own_urls(self):
        requirement = CubRequirementFactory(slug="switcher")
        RequirementRecordFactory(requirement=requirement, year=self.year, member=ActiveScoutFactory())

        response = self.client.get(reverse("compliance:dashboard"))

        available = response.context["years"]["available"]
        self.assertTrue(available)
        self.assertTrue(all("url" in entry and "year" in entry for entry in available))

    def test_unknown_year_falls_back_to_the_current_one(self):
        response = self.client.get(reverse("compliance:dashboard_by_year", kwargs={"year": 1899}))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["years"]["viewing"], self.year)


class EmptyStateTestCase(ComplianceViewTestCase):
    def test_dashboard_renders_with_no_families(self):
        FamilyFactory()
        self.login(self.leader)

        response = self.client.get(reverse("compliance:dashboard"))

        self.assertEqual(response.status_code, HTTPStatus.OK)


class SiteIntegrationTestCase(ComplianceViewTestCase):
    """The tabs, navbar entries, and member detail cards added to membership."""

    DIRECTORY_URLS = ("membership:scouts", "membership:parents", "membership:all")

    def test_directory_pages_still_render_after_the_tabs_were_extracted(self):
        self.login(self.parent)

        for name in self.DIRECTORY_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))

                self.assertEqual(response.status_code, HTTPStatus.OK)
                for tab in ("Cubs", "Adults", "All Members", "Dens"):
                    self.assertContains(response, tab)

    def dashboard_link(self):
        # Match the href exactly. The bare path is a prefix of the my-family
        # URL, which every member sees.
        return f'href="{reverse("compliance:dashboard")}"'

    def test_requirements_tab_is_hidden_from_a_plain_parent(self):
        self.login(self.parent)

        response = self.client.get(reverse("membership:scouts"))

        self.assertNotContains(response, self.dashboard_link())

    def test_requirements_tab_is_shown_to_leadership(self):
        self.login(self.leader)

        response = self.client.get(reverse("membership:scouts"))

        self.assertContains(response, self.dashboard_link())

    def test_my_requirements_is_offered_to_every_member(self):
        self.login(self.parent)

        response = self.client.get(reverse("membership:scouts"))

        self.assertContains(response, reverse("compliance:my_family"))


class MemberProfileMembershipTestCase(ComplianceViewTestCase):
    """
    Member profile pages carry no compliance information at all.

    Profiles are reachable by every logged-in member, and what a family owes is
    nobody else's business. Each audience has a gated page already: My
    Requirements for your own family, the dashboard for leadership.
    """

    def setUp(self):
        super().setUp()
        self.cub = self.family.children.first()
        self.login(self.parent)

    def register(self, member, expires_on, membership_id="137042891"):
        member.scouting_membership_id = membership_id
        member.scouting_membership_expires_on = expires_on
        member.save()

    def scout_page(self, scout=None):
        return self.client.get(reverse("membership:scout_detail", kwargs={"slug": (scout or self.cub).slug}))

    def test_your_own_cub_s_profile_carries_no_requirements(self):
        requirement = CubRequirementFactory(slug="profile-own")
        RequirementRecordFactory(requirement=requirement, year=self.year, member=self.cub)

        response = self.scout_page()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, "Membership Requirements")
        self.assertNotContains(response, requirement.name)

    def test_your_own_cub_s_profile_carries_no_registration(self):
        self.register(self.cub, timezone.localdate() + datetime.timedelta(days=30))

        response = self.scout_page()

        self.assertNotContains(response, "137042891")
        self.assertNotContains(response, "Expiring Soon")

    def test_an_adult_profile_carries_neither(self):
        requirement = AdultRequirementFactory(slug="profile-adult")
        RequirementRecordFactory(requirement=requirement, year=self.year, member=self.parent)
        self.register(self.parent, timezone.localdate() - datetime.timedelta(days=1))

        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.parent.slug}))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, "Membership Requirements")
        self.assertNotContains(response, requirement.name)
        self.assertNotContains(response, "137042891")

    def test_leadership_gets_nothing_extra_on_a_profile_either(self):
        """The dashboard is where leadership looks. The profile is not a second one."""
        self.register(self.cub, timezone.localdate() - datetime.timedelta(days=1))
        self.login(self.leader)

        response = self.scout_page()

        self.assertNotContains(response, "Membership Requirements")
        self.assertNotContains(response, "137042891")

    def test_another_family_s_registration_is_not_exposed(self):
        other = self.leader_family.children.first()
        self.register(other, timezone.localdate() + datetime.timedelta(days=30), membership_id="999888777")

        response = self.scout_page(other)

        self.assertNotContains(response, "Membership Requirements")
        self.assertNotContains(response, "999888777")

    def test_the_profile_still_renders_the_member(self):
        """Removing the card must not take the rest of the page with it."""
        response = self.scout_page()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.cub.get_short_name())


class MatrixCellStateTestCase(ComplianceViewTestCase):
    """
    The dashboard cell reports one state per family and requirement. Partly
    done reads yellow so a family with one parent's medical form on file does
    not look identical to one with none.
    """

    def setUp(self):
        super().setUp()
        self.login(self.leader)
        self.requirement = AdultRequirementFactory(slug="medical-adult-state")
        # Two adults in the family, so partial completion is possible.
        self.adults = list(self.family.adults.all())
        while len(self.adults) < 2:
            self.adults.append(AdultFactory(family=self.family))

    def cell_for(self, family):
        response = self.client.get(reverse("compliance:dashboard"))
        row = next(r for r in response.context["families"]["rows"] if r["family"] == family)
        index = [r.slug for r in response.context["requirements"]].index(self.requirement.slug)
        return row["cells"][index]

    def record(self, adult, **kwargs):
        return RequirementRecordFactory(requirement=self.requirement, year=self.year, member=adult, **kwargs)

    def test_none_complete_reads_not_started(self):
        for adult in self.adults:
            self.record(adult)

        self.assertEqual(self.cell_for(self.family)["state"], "outstanding")

    def test_one_of_two_complete_reads_partial(self):
        self.record(self.adults[0], status=RequirementRecord.Status.COMPLETE)
        self.record(self.adults[1])

        cell = self.cell_for(self.family)
        self.assertEqual(cell["state"], "partial")
        self.assertEqual(cell["outstanding"], 1)
        self.assertEqual(cell["total"], 2)

    def test_all_complete_reads_complete(self):
        for adult in self.adults:
            self.record(adult, status=RequirementRecord.Status.COMPLETE)

        self.assertEqual(self.cell_for(self.family)["state"], "complete")

    def test_a_waived_record_counts_as_done(self):
        self.record(self.adults[0], status=RequirementRecord.Status.WAIVED)
        self.record(self.adults[1])

        self.assertEqual(self.cell_for(self.family)["state"], "partial")

    def test_partly_done_families_still_match_the_outstanding_filter(self):
        self.record(self.adults[0], status=RequirementRecord.Status.COMPLETE)
        self.record(self.adults[1])

        response = self.client.get(reverse("compliance:dashboard"), {"filter": "outstanding"})

        self.assertIn(self.family, [row["family"] for row in response.context["families"]["rows"]])

    def test_partial_renders_a_yellow_badge(self):
        self.record(self.adults[0], status=RequirementRecord.Status.COMPLETE)
        self.record(self.adults[1])

        response = self.client.get(reverse("compliance:dashboard"))

        self.assertContains(response, "still to do")
        self.assertContains(response, "text-bg-warning")


class ScoutingMembershipDashboardTestCase(ComplianceViewTestCase):
    """
    The registration card on the dashboard, which reads the Cubs directly
    rather than any Requirement record.
    """

    def setUp(self):
        super().setUp()
        self.login(self.leader)
        # The base fixture gives both families one active Cub, so the year has
        # two; self.cub is the one these tests register.
        self.cub = self.family.children.first()
        self.other_cub = self.leader_family.children.first()

    def register(self, membership_id, expires_on):
        self.cub.scouting_membership_id = membership_id
        self.cub.scouting_membership_expires_on = expires_on
        self.cub.save()

    def get_dashboard(self):
        response = self.client.get(reverse("compliance:dashboard"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response

    def test_a_current_registration_reads_as_registered(self):
        self.register("12345678", timezone.localdate() + datetime.timedelta(days=30))

        summary = self.get_dashboard().context["scouting_membership"]

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["current"], 1)
        # The other family's Cub has nothing on file.
        self.assertEqual(summary["outstanding"], 1)

    def test_a_lapsed_registration_reads_as_expired(self):
        self.register("12345678", timezone.localdate() - datetime.timedelta(days=1))

        response = self.get_dashboard()

        self.assertEqual(response.context["scouting_membership"]["expired"], 1)
        self.assertContains(response, "Expired")
        self.assertContains(response, "12345678")

    def test_nothing_on_file_reads_as_not_on_file(self):
        response = self.get_dashboard()

        summary = response.context["scouting_membership"]
        self.assertEqual(summary["missing"], 2)
        self.assertEqual(summary["outstanding"], summary["total"])
        self.assertContains(response, "Not on file")

    def test_the_card_names_the_cub_and_its_expiration_date(self):
        self.register("12345678", timezone.localdate() + datetime.timedelta(days=30))

        response = self.get_dashboard()

        self.assertContains(response, "Scouting America registration")
        self.assertContains(response, str(self.cub))
        self.assertContains(response, "Membership ID")

    def test_nothing_on_file_stays_grey_here_and_a_lapsed_one_reads_red(self):
        """
        Grey, where the family page badges the same standing amber. This is
        leadership's own worklist rather than a page telling one family what
        they owe, and nothing on file is its ordinary starting state.
        """
        self.register("12345678", timezone.localdate() - datetime.timedelta(days=1))

        response = self.get_dashboard()

        self.assertEqual(self.badge_class_for(response, "Not on file"), "text-bg-secondary")
        self.assertEqual(self.badge_class_for(response, "Expired"), "text-bg-danger")

    def test_the_progress_bar_colours_match_the_badges(self):
        self.register("12345678", timezone.localdate() + datetime.timedelta(days=200))

        response = self.get_dashboard()

        # One registered Cub and one with nothing on file: green and grey.
        self.assertContains(response, "progress-bar bg-success")
        self.assertContains(response, "progress-bar bg-secondary")
        self.assertNotContains(response, "progress-bar bg-warning")

    def test_it_does_not_depend_on_any_requirement_record(self):
        """The whole point: no Requirement is seeded or recorded against."""
        Requirement.objects.all().delete()
        self.register("12345678", timezone.localdate() - datetime.timedelta(days=1))

        response = self.get_dashboard()

        self.assertEqual(RequirementRecord.objects.count(), 0)
        self.assertEqual(response.context["scouting_membership"]["expired"], 1)
        self.assertContains(response, "Expired")

    def test_it_follows_the_year_switcher(self):
        # Explicit dates: PackYearFactory picks a random start day, which can
        # land a second year on top of today and make current() ambiguous.
        other_year = PackYearFactory(
            year=self.year.year - 1,
            start_date=self.year.start_date - datetime.timedelta(days=365),
            end_date=self.year.start_date - datetime.timedelta(days=1),
        )

        response = self.client.get(reverse("compliance:dashboard_by_year", kwargs={"year": other_year.year}))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["scouting_membership"]["total"], 0)

    def test_the_card_does_not_scale_queries_with_cubs(self):
        def count(cubs):
            while ActiveScout.objects.filter(status=ActiveScout.ACTIVE).count() < cubs:
                CompleteFamilyFactory(adults=1, active_children=1)
            cache.clear()
            self.client.get(reverse("compliance:dashboard"))
            cache.clear()
            with CaptureQueriesContext(connection) as captured:
                self.client.get(reverse("compliance:dashboard"))
            return len(captured.captured_queries)

        self.assertEqual(count(4), count(10))


class CollapsibleSectionsTestCase(ComplianceViewTestCase):
    """
    Both tables collapse; their totals stay in the header either way, which is
    the point of collapsing them.
    """

    def setUp(self):
        super().setUp()
        self.login(self.leader)

    def test_both_tables_are_collapsible(self):
        response = self.client.get(reverse("compliance:dashboard"))

        self.assertContains(response, 'data-bs-target="#scouting-membership"')
        self.assertContains(response, 'id="scouting-membership" class="collapse"')
        self.assertContains(response, 'data-bs-target="#by-family"')
        self.assertContains(response, 'id="by-family" class="collapse"')

    def test_the_headers_carry_the_totals(self):
        response = self.client.get(reverse("compliance:dashboard"))

        self.assertContains(response, "of 2 Cubs registered")
        self.assertContains(response, "families square")

    def test_family_totals_count_the_whole_pack(self):
        requirement = FamilyRequirementFactory(slug="collapse-dues")
        requirement.sync_records(year=self.year)
        RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="collapse-cub"),
            year=self.year,
            member=self.family.children.first(),
            status=RequirementRecord.Status.COMPLETE,
        )

        families = self.client.get(reverse("compliance:dashboard")).context["families"]

        self.assertEqual(families["total"], 2)
        self.assertEqual(families["outstanding"], 2)
        self.assertEqual(families["complete"], 0)

    def test_totals_ignore_the_outstanding_filter(self):
        """
        The header says how many families are square out of the whole pack, so
        it must not shrink to match a filtered table.
        """
        requirement = FamilyRequirementFactory(slug="collapse-filtered")
        requirement.sync_records(year=self.year)
        record = RequirementRecord.objects.get(requirement=requirement, family=self.family)
        record.status = RequirementRecord.Status.COMPLETE
        record.save()

        unfiltered = self.client.get(reverse("compliance:dashboard")).context["families"]
        filtered = self.client.get(reverse("compliance:dashboard"), {"filter": "outstanding"}).context["families"]

        self.assertEqual(unfiltered["total"], filtered["total"])
        self.assertEqual(unfiltered["complete"], filtered["complete"])
        self.assertEqual(len(unfiltered["rows"]), 2)
        self.assertEqual(len(filtered["rows"]), 1)

    def test_a_family_with_nothing_outstanding_counts_as_square(self):
        requirement = FamilyRequirementFactory(slug="collapse-square")
        requirement.sync_records(year=self.year)
        RequirementRecord.objects.filter(requirement=requirement).update(status=RequirementRecord.Status.COMPLETE)

        families = self.client.get(reverse("compliance:dashboard")).context["families"]

        self.assertEqual(families["complete"], families["total"])
        self.assertEqual(families["outstanding"], 0)
