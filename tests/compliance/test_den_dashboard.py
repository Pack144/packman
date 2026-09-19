from http import HTTPStatus

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.committees.models import Committee, CommitteeMember
from packman.compliance.factories import (
    AdultRequirementFactory,
    CubRequirementFactory,
    FamilyRequirementFactory,
    RequirementRecordFactory,
)
from packman.compliance.models import RequirementRecord
from packman.dens.factories import DenFactory, MembershipFactory
from packman.membership.factories import AdultFactory, CompleteFamilyFactory, ScoutFactory

from .test_views import grant_leadership


def make_den_leader(adult, year, den):
    """
    Make an Adult a Den Leader the way the site really does.

    A den assignment is a CommitteeMember row carrying a den, which is what
    committees.leadership.led_dens() reads -- not a permission and not a Group.
    """
    committee, _ = Committee.objects.get_or_create(
        slug="den-leaders", defaults={"name": "Den Leaders", "leadership": True}
    )
    return CommitteeMember.objects.create(
        committee=committee,
        member=adult,
        year=year,
        den=den,
        position=CommitteeMember.Position.DEN_LEADER,
    )


def family_in_den(den, year, adults=1, cubs=1):
    """A family whose Cubs are all assigned to one den for one pack year."""
    family = CompleteFamilyFactory(adults=adults)
    for _ in range(cubs):
        MembershipFactory(scout=ScoutFactory(family=family), den=den, year_assigned=year)
    return family


class DenDashboardTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.den = DenFactory(number=3)
        cls.other_den = DenFactory(number=5)

        cls.family = family_in_den(cls.den, cls.year)
        cls.cub = cls.family.children.first()
        cls.parent = cls.family.adults.first()

        cls.other_family = family_in_den(cls.other_den, cls.year)

        cls.leader = AdultFactory()
        make_den_leader(cls.leader, cls.year, cls.den)

    def setUp(self):
        # PackYear.objects.current() is cached, and every test here builds its
        # own years.
        cache.clear()

    def login(self, adult):
        self.client.force_login(adult)

    def get(self, **params):
        return self.client.get(reverse("compliance:den_dashboard"), params)

    def subjects(self, response):
        return [group["subject"] for row in response.context["rows"] for group in row["groups"]]


class DenDashboardAccessTestCase(DenDashboardTestCase):
    def test_anonymous_is_redirected(self):
        response = self.get()

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_parent_without_a_den_assignment_is_forbidden(self):
        self.login(self.parent)

        response = self.get()

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_den_leader_may_view(self):
        self.login(self.leader)

        response = self.get()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["den"], self.den)

    def test_pack_leadership_may_view_without_a_den_assignment(self):
        leadership = AdultFactory()
        grant_leadership(leadership, self.year, "view_all_records")
        self.login(leadership)

        response = self.get()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["available_dens"], [self.den, self.other_den])

    def test_a_den_the_viewer_does_not_lead_is_not_found(self):
        """The query parameter is the authorization boundary, so it 404s
        rather than quietly falling back to a den they do lead."""
        self.login(self.leader)

        response = self.get(den=self.other_den.number)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_a_second_den_the_viewer_leads_may_be_selected(self):
        make_den_leader(self.leader, self.year, self.other_den)
        self.login(self.leader)

        response = self.get(den=self.other_den.number)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["den"], self.other_den)


class DenDashboardScopeTestCase(DenDashboardTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.leader)

    def test_lists_the_cubs_and_parents_of_the_den(self):
        response = self.get()

        subjects = self.subjects(response)
        self.assertIn(self.cub, subjects)
        self.assertIn(self.parent, subjects)

    def test_excludes_families_from_another_den(self):
        response = self.get()

        families = [row["family"] for row in response.context["rows"]]
        self.assertEqual(families, [self.family])

    def test_shows_household_requirements(self):
        dues = FamilyRequirementFactory(name="Pack Dues", slug="pack-dues-den")
        RequirementRecordFactory(requirement=dues, year=self.year, member=None, family=self.family)

        response = self.get()

        self.assertIn(self.family, self.subjects(response))

    def test_a_sibling_in_another_den_is_left_out(self):
        """
        The records hang off the shared family, but that Cub is another
        leader's to chase.
        """
        sibling = ScoutFactory(family=self.family)
        MembershipFactory(scout=sibling, den=self.other_den, year_assigned=self.year)
        requirement = CubRequirementFactory(name="Medical Form", slug="medical-form-den")
        RequirementRecordFactory(requirement=requirement, year=self.year, member=sibling)

        response = self.get()

        self.assertNotIn(sibling, self.subjects(response))

    def test_a_cub_with_no_family_still_appears(self):
        orphan = ScoutFactory(family=None)
        MembershipFactory(scout=orphan, den=self.den, year_assigned=self.year)

        response = self.get()

        self.assertIn(orphan, self.subjects(response))

    def test_counts_outstanding_records_across_the_den(self):
        cub_requirement = CubRequirementFactory(name="Health Form", slug="health-form-den")
        adult_requirement = AdultRequirementFactory(name="Youth Protection", slug="ypt-den")
        RequirementRecordFactory(requirement=cub_requirement, year=self.year, member=self.cub)
        RequirementRecordFactory(
            requirement=adult_requirement,
            year=self.year,
            member=self.parent,
            status=RequirementRecord.Status.COMPLETE,
        )

        response = self.get()

        standings = {standing.name: standing for standing in response.context["requirements"]}
        self.assertEqual(standings["Health Form"].outstanding, 1)
        self.assertEqual(standings["Youth Protection"].complete, 1)

    def test_requirement_bars_do_not_link_to_the_pack_wide_roster(self):
        """A den leader has no compliance.view_all_records, so that link 403s."""
        requirement = CubRequirementFactory(name="Linkless", slug="linkless-den")
        RequirementRecordFactory(requirement=requirement, year=self.year, member=self.cub)

        response = self.get()

        self.assertNotContains(response, reverse("compliance:roster", kwargs={"slug": "linkless-den"}))


class DenDashboardYearTestCase(DenDashboardTestCase):
    def setUp(self):
        super().setUp()
        # Dates left unset so PackYear.save() derives a window that does not
        # straddle today; PackYearFactory's own random dates can, which makes
        # PackYear.objects.current() raise MultipleObjectsReturned. See
        # CurrentPackYearFactory's docstring.
        self.past = PackYearFactory(year=self.year.year - 1, start_date=None, end_date=None)
        self.login(self.leader)

    def url_for(self, year):
        return reverse("compliance:den_dashboard_by_year", kwargs={"year": year.year})

    def test_shows_the_den_led_in_the_year_being_viewed(self):
        make_den_leader(self.leader, self.past, self.other_den)
        family_in_den(self.other_den, self.past)

        response = self.client.get(self.url_for(self.past))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["den"], self.other_den)

    def test_a_year_the_viewer_led_no_den_is_empty_rather_than_forbidden(self):
        response = self.client.get(self.url_for(self.past))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(response.context["den"])


class DenDashboardQueryTestCase(DenDashboardTestCase):
    def setUp(self):
        super().setUp()
        self.requirement = CubRequirementFactory(name="Scaling", slug="scaling-den")
        self.login(self.leader)

    def test_does_not_scale_queries_with_den_size(self):
        """
        Guards the den summary against slipping into a per-family query, which
        is what campaigns' leaderboard does.
        """
        # One request first, measured by nobody: django.contrib.sites keeps a
        # process-level SITE_CACHE that cache.clear() does not touch, so the
        # first render in a process costs a query the rest do not.
        self.get()

        baseline = self.count_queries(families=2)
        grown = self.count_queries(families=8)

        self.assertEqual(grown, baseline)

    def count_queries(self, families):
        while self.den.scouts.filter(year_assigned=self.year).count() < families:
            family_in_den(self.den, self.year, adults=2)
        self.requirement.sync_records(year=self.year)
        cache.clear()

        with CaptureQueriesContext(connection) as captured:
            self.get()
        return len(captured.captured_queries)
