from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from packman.calendars.factories import CurrentPackYearFactory
from packman.committees.models import Committee, CommitteeMember
from packman.compliance.factories import (
    AdultRequirementFactory,
    CubRequirementFactory,
    ExpiredRecordFactory,
    ExpiringRecordFactory,
    FamilyRequirementFactory,
    RequirementRecordFactory,
)
from packman.compliance.models import RequirementRecord
from packman.membership.factories import ActiveScoutFactory, AdultFactory, CompleteFamilyFactory, FamilyFactory
from packman.membership.models import Adult, Family


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


class DashboardContentTestCase(ComplianceViewTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.leader)
        self.requirement = CubRequirementFactory(slug="content-cub")

    def test_rollup_counts_each_state(self):
        scouts = [ActiveScoutFactory() for _ in range(3)]
        RequirementRecordFactory(requirement=self.requirement, year=self.year, member=scouts[0])
        ExpiredRecordFactory(requirement=self.requirement, year=self.year, member=scouts[1])
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
        self.assertEqual(rollup.expired, 1)
        self.assertEqual(rollup.waived, 1)

    def test_matrix_lists_active_families(self):
        response = self.client.get(reverse("compliance:dashboard"))

        families = {row["family"] for row in response.context["matrix"]}
        self.assertIn(self.family, families)

    def test_filter_narrows_to_families_with_expired_items(self):
        dues = FamilyRequirementFactory(slug="content-dues")
        ExpiredRecordFactory(requirement=dues, year=self.year, member=None, family=self.family)
        RequirementRecordFactory(
            requirement=dues,
            year=self.year,
            member=None,
            family=self.leader_family,
            status=RequirementRecord.Status.COMPLETE,
        )

        response = self.client.get(reverse("compliance:dashboard"), {"filter": "expired"})

        families = [row["family"] for row in response.context["matrix"]]
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

    def test_card_appears_on_a_cub_in_your_own_family(self):
        requirement = CubRequirementFactory(slug="card-own")
        scout = self.family.children.first()
        RequirementRecordFactory(requirement=requirement, year=self.year, member=scout)
        self.login(self.parent)

        response = self.client.get(reverse("membership:scout_detail", kwargs={"slug": scout.slug}))

        self.assertContains(response, "Membership Requirements")
        self.assertContains(response, requirement.name)

    def test_card_is_hidden_on_another_family_s_cub(self):
        requirement = CubRequirementFactory(slug="card-other")
        scout = self.leader_family.children.first()
        RequirementRecordFactory(requirement=requirement, year=self.year, member=scout)
        self.login(self.parent)

        response = self.client.get(reverse("membership:scout_detail", kwargs={"slug": scout.slug}))

        self.assertNotContains(response, "Membership Requirements")

    def test_leadership_sees_the_card_on_any_cub(self):
        requirement = CubRequirementFactory(slug="card-leader")
        scout = self.family.children.first()
        RequirementRecordFactory(requirement=requirement, year=self.year, member=scout)
        self.login(self.leader)

        response = self.client.get(reverse("membership:scout_detail", kwargs={"slug": scout.slug}))

        self.assertContains(response, "Membership Requirements")

    def test_card_appears_on_an_adult_page(self):
        requirement = AdultRequirementFactory(slug="card-adult")
        RequirementRecordFactory(requirement=requirement, year=self.year, member=self.parent)
        self.login(self.parent)

        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.parent.slug}))

        self.assertContains(response, "Membership Requirements")


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
        row = next(r for r in response.context["matrix"] if r["family"] == family)
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

    def test_expired_still_wins_over_partial(self):
        ExpiredRecordFactory(requirement=self.requirement, year=self.year, member=self.adults[0])
        self.record(self.adults[1])

        self.assertEqual(self.cell_for(self.family)["state"], "expired")

    def test_expiring_reads_expiring_when_nothing_is_outstanding(self):
        ExpiringRecordFactory(requirement=self.requirement, year=self.year, member=self.adults[0])
        self.record(self.adults[1], status=RequirementRecord.Status.COMPLETE)

        self.assertEqual(self.cell_for(self.family)["state"], "expiring")

    def test_partly_done_families_still_match_the_outstanding_filter(self):
        self.record(self.adults[0], status=RequirementRecord.Status.COMPLETE)
        self.record(self.adults[1])

        response = self.client.get(reverse("compliance:dashboard"), {"filter": "outstanding"})

        self.assertIn(self.family, [row["family"] for row in response.context["matrix"]])

    def test_partial_renders_a_yellow_badge(self):
        self.record(self.adults[0], status=RequirementRecord.Status.COMPLETE)
        self.record(self.adults[1])

        response = self.client.get(reverse("compliance:dashboard"))

        self.assertContains(response, "still to do")
        self.assertContains(response, "text-bg-warning")
