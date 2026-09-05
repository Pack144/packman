import datetime

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.committees.factories import (
    AkelaFactory,
    AssistantAkelaFactory,
    CommitteeFactory,
    CommitteeMemberFactory,
    DenLeaderFactory,
    LeadershipCommitteeFactory,
)
from packman.compliance.factories import (
    AdultRequirementFactory,
    CubRequirementFactory,
    FamilyRequirementFactory,
    LeaderRequirementFactory,
    RequirementFactory,
    RequirementRecordFactory,
    ScoutingMembershipCubFactory,
)
from packman.compliance.models import Requirement, RequirementRecord
from packman.membership.factories import ActiveScoutFactory, AdultFactory, CompleteFamilyFactory, FamilyFactory
from packman.membership.models import Adult


class RequirementQuerySetTestCase(TestCase):
    def test_active_excludes_retired_requirements(self):
        live = CubRequirementFactory(slug="live")
        CubRequirementFactory(slug="retired", is_active=False)

        self.assertIn(live, Requirement.objects.active())
        self.assertEqual(Requirement.objects.active().filter(slug="retired").count(), 0)

    def test_for_audience(self):
        cub = CubRequirementFactory(slug="cub-thing")
        adult = AdultRequirementFactory(slug="adult-thing")

        self.assertIn(cub, Requirement.objects.for_audience(Requirement.Audience.CUB))
        self.assertNotIn(adult, Requirement.objects.for_audience(Requirement.Audience.CUB))


class RequirementRecordQuerySetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.requirement = CubRequirementFactory(slug="qs-requirement")

    def setUp(self):
        cache.clear()

    def make(self, factory=RequirementRecordFactory, **kwargs):
        kwargs.setdefault("member", ActiveScoutFactory())
        return factory(requirement=self.requirement, year=self.year, **kwargs)

    def test_outstanding(self):
        outstanding = self.make()
        self.make(status=RequirementRecord.Status.COMPLETE)

        self.assertEqual(list(RequirementRecord.objects.outstanding()), [outstanding])

    def test_waived_is_not_outstanding(self):
        self.make(status=RequirementRecord.Status.WAIVED)

        self.assertFalse(RequirementRecord.objects.outstanding().exists())

    def test_complete(self):
        self.make()
        complete = self.make(status=RequirementRecord.Status.COMPLETE)

        self.assertEqual(list(RequirementRecord.objects.complete()), [complete])

    def test_waived(self):
        self.make()
        waived = self.make(status=RequirementRecord.Status.WAIVED)

        self.assertEqual(list(RequirementRecord.objects.waived()), [waived])

    def test_for_year(self):
        this_year = self.make()
        other = PackYearFactory(year=self.year.year - 1)
        RequirementRecordFactory(requirement=self.requirement, year=other, member=ActiveScoutFactory())

        self.assertEqual(list(RequirementRecord.objects.for_year(self.year)), [this_year])

    def test_for_family(self):
        family = FamilyFactory()
        mine = self.make(member=ActiveScoutFactory(family=family))
        self.make()

        self.assertEqual(list(RequirementRecord.objects.for_family(family)), [mine])


class SyncRecordsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()

    def setUp(self):
        cache.clear()

    def test_opens_a_record_for_each_active_cub(self):
        requirement = CubRequirementFactory(slug="cub-sync")
        ActiveScoutFactory()
        ActiveScoutFactory()

        created = requirement.sync_records(year=self.year)

        self.assertEqual(len(created), 2)
        self.assertEqual(requirement.records.count(), 2)

    def test_skips_inactive_cubs(self):
        from packman.membership.factories import ScoutFactory

        requirement = CubRequirementFactory(slug="cub-sync-inactive")
        ScoutFactory()  # no den membership, so not active

        self.assertEqual(len(requirement.sync_records(year=self.year)), 0)

    def test_is_idempotent(self):
        requirement = CubRequirementFactory(slug="idempotent")
        ActiveScoutFactory()

        requirement.sync_records(year=self.year)
        second = requirement.sync_records(year=self.year)

        self.assertEqual(len(second), 0)
        self.assertEqual(requirement.records.count(), 1)

    def test_backfills_family_despite_bulk_create(self):
        """bulk_create() skips save(), so sync has to set the family itself."""
        requirement = CubRequirementFactory(slug="family-backfill")
        family = FamilyFactory()
        ActiveScoutFactory(family=family)

        requirement.sync_records(year=self.year)

        self.assertEqual(requirement.records.get().family, family)

    def test_family_requirement_opens_one_record_per_family(self):
        """
        The regression test for FamilyQuerySet.active() returning a row per
        active child: a family with two Cubs must still get a single record.
        """
        requirement = FamilyRequirementFactory(slug="dues-sync")
        CompleteFamilyFactory(active_children=2)

        created = requirement.sync_records(year=self.year)

        self.assertEqual(len(created), 1)
        self.assertEqual(requirement.records.count(), 1)

    def test_adult_requirement_covers_parents_of_active_cubs(self):
        requirement = AdultRequirementFactory(slug="adult-sync")
        family = CompleteFamilyFactory(adults=2, active_children=1)

        requirement.sync_records(year=self.year)

        self.assertEqual(requirement.records.count(), 2)
        self.assertEqual(set(requirement.records.values_list("family_id", flat=True)), {family.pk})

    def test_contributors_are_excluded_by_default(self):
        requirement = AdultRequirementFactory(slug="no-contributors", include_contributors=False)
        CompleteFamilyFactory(adults=1, active_children=1)
        AdultFactory(family=None, role=Adult.CONTRIBUTOR)

        requirement.sync_records(year=self.year)

        self.assertEqual(requirement.records.count(), 1)

    def test_contributors_are_included_when_opted_in(self):
        requirement = AdultRequirementFactory(slug="with-contributors", include_contributors=True)
        CompleteFamilyFactory(adults=1, active_children=1)
        AdultFactory(family=None, role=Adult.CONTRIBUTOR)

        requirement.sync_records(year=self.year)

        self.assertEqual(requirement.records.count(), 2)

    def test_can_sync_a_year_that_is_not_the_current_one(self):
        """active() is pinned to the current year; active_in() is what makes this possible."""
        requirement = CubRequirementFactory(slug="next-year")
        next_year = PackYearFactory(year=self.year.year + 1)
        scout = ActiveScoutFactory()
        scout.den_memberships.create(den=scout.den_memberships.get().den, year_assigned=next_year)

        created = requirement.sync_records(year=next_year)

        self.assertEqual(len(created), 1)
        self.assertEqual(requirement.records.get().year, next_year)

    def test_records_open_as_not_started(self):
        requirement = CubRequirementFactory(slug="status-check")
        ActiveScoutFactory()

        requirement.sync_records(year=self.year)

        self.assertEqual(requirement.records.get().status, RequirementRecord.Status.NOT_STARTED)


class SubjectsForTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()

    def setUp(self):
        cache.clear()

    def test_family_subjects_are_deduplicated(self):
        """A family with two active Cubs must appear once, not twice."""
        requirement = FamilyRequirementFactory(slug="dedupe")
        CompleteFamilyFactory(active_children=3)

        self.assertEqual(requirement.subjects_for(self.year).count(), 1)

    def test_cub_subjects(self):
        requirement = RequirementFactory(slug="cub-subjects", applies_to=Requirement.Audience.CUB)
        ActiveScoutFactory()

        self.assertEqual(requirement.subjects_for(self.year).count(), 1)


class LeaderSubjectsTestCase(TestCase):
    """Who a Pack Leader requirement is asked of."""

    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.requirement = LeaderRequirementFactory(slug="leader-subjects")

    def setUp(self):
        cache.clear()

    def subjects(self):
        return set(self.requirement.subjects_for(self.year))

    def test_the_three_leadership_positions_are_subjects(self):
        akela = AkelaFactory(year=self.year).member
        assistant = AssistantAkelaFactory(year=self.year).member
        den_leader = DenLeaderFactory(year=self.year).member

        self.assertEqual(self.subjects(), {akela, assistant, den_leader})

    def test_ordinary_committee_members_are_not(self):
        CommitteeMemberFactory(year=self.year, committee=CommitteeFactory(name="Popcorn", slug="popcorn"))

        self.assertEqual(self.subjects(), set())

    def test_a_leadership_committee_named_for_the_title_counts(self):
        """Mirrors assignment_title()'s fallback for packs that record it that way."""
        assignment = CommitteeMemberFactory(
            year=self.year,
            committee=LeadershipCommitteeFactory(name="Den Leaders", slug="den-leaders"),
        )

        self.assertEqual(self.subjects(), {assignment.member})

    def test_a_leadership_committee_not_named_for_a_title_does_not(self):
        CommitteeMemberFactory(
            year=self.year,
            committee=LeadershipCommitteeFactory(name="Pack Committee", slug="pack-committee"),
        )

        self.assertEqual(self.subjects(), set())

    def test_leadership_in_another_year_does_not_carry_over(self):
        """
        The year and the position have to hold of the same assignment, or a
        past Den Leader who now runs popcorn would read as leadership today.
        """
        adult = AkelaFactory(year=PackYearFactory(year=self.year.year - 1)).member
        CommitteeMemberFactory(
            member=adult, year=self.year, committee=CommitteeFactory(name="Popcorn", slug="popcorn")
        )

        self.assertEqual(self.subjects(), set())

    def test_a_leader_is_listed_once_however_many_hats_they_wear(self):
        adult = AdultFactory()
        AkelaFactory(member=adult, year=self.year)
        DenLeaderFactory(member=adult, year=self.year, committee=CommitteeFactory(name="Dens", slug="dens"))

        self.assertEqual(self.requirement.subjects_for(self.year).count(), 1)

    def test_deactivated_accounts_are_excluded(self):
        AkelaFactory(year=self.year, member=AdultFactory(is_active=False))

        self.assertEqual(self.subjects(), set())


class EffectiveStatusAnnotationTestCase(TestCase):
    """
    The annotation and the property are two spellings of one rule; assert they
    never disagree. See tests/compliance/test_derived.py for the rule itself.
    """

    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.derived = ScoutingMembershipCubFactory(slug="annotated-sa-cub")
        cls.manual = CubRequirementFactory(slug="annotated-manual-cub")

    def setUp(self):
        cache.clear()

    def build_every_case(self):
        today = timezone.localdate()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        for membership_id, expires_on in (
            ("", None),
            ("12345678", None),
            ("", tomorrow),
            ("12345678", tomorrow),
            ("12345678", today),
            ("12345678", yesterday),
        ):
            for requirement in (self.derived, self.manual):
                for status in RequirementRecord.Status.values:
                    if status == RequirementRecord.Status.EXPIRED:
                        continue  # never stored
                    RequirementRecordFactory(
                        requirement=requirement,
                        year=self.year,
                        status=status,
                        member=ActiveScoutFactory(
                            scouting_membership_id=membership_id,
                            scouting_membership_expires_on=expires_on,
                        ),
                    )

    def test_annotation_matches_the_property_for_every_case(self):
        self.build_every_case()

        annotated = RequirementRecord.objects.with_effective_status().select_related("requirement", "member")

        # Guard against the comparison below passing vacuously, or over a set of
        # fixtures that never reaches the interesting states.
        self.assertEqual(
            {record.effective_status for record in annotated},
            set(RequirementRecord.Status.values),
        )
        for record in annotated:
            with self.subTest(requirement=record.requirement.slug, stored=record.status):
                self.assertEqual(record._effective_status, record.effective_status)

    def test_outstanding_covers_not_started_and_expired(self):
        self.build_every_case()

        outstanding = set(RequirementRecord.objects.outstanding())
        self.assertTrue(outstanding)
        expected = {
            record
            for record in RequirementRecord.objects.all()
            if record.effective_status in (RequirementRecord.Status.NOT_STARTED, RequirementRecord.Status.EXPIRED)
        }

        self.assertEqual(outstanding, expected)

    def test_a_lapsed_registration_is_not_complete(self):
        record = RequirementRecordFactory(
            requirement=self.derived,
            year=self.year,
            status=RequirementRecord.Status.COMPLETE,
            member=ActiveScoutFactory(
                scouting_membership_id="12345678",
                scouting_membership_expires_on=timezone.localdate() - datetime.timedelta(days=1),
            ),
        )

        self.assertNotIn(record, RequirementRecord.objects.complete())
        self.assertIn(record, RequirementRecord.objects.expired())
        self.assertIn(record, RequirementRecord.objects.outstanding())

    def test_as_of_lets_the_caller_ask_about_another_day(self):
        expires_on = timezone.localdate() + datetime.timedelta(days=10)
        record = RequirementRecordFactory(
            requirement=self.derived,
            year=self.year,
            member=ActiveScoutFactory(scouting_membership_id="12345678", scouting_membership_expires_on=expires_on),
        )

        self.assertIn(record, RequirementRecord.objects.complete())
        self.assertIn(
            record,
            RequirementRecord.objects.expired(as_of=expires_on + datetime.timedelta(days=1)),
        )

    def test_annotating_twice_is_harmless(self):
        """complete() annotates, and callers may have annotated already."""
        self.build_every_case()

        twice = RequirementRecord.objects.with_effective_status().with_effective_status()

        self.assertEqual(twice.count(), RequirementRecord.objects.count())
