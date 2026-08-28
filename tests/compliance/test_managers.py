from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.compliance.factories import (
    AdultRequirementFactory,
    CubRequirementFactory,
    ExpiredRecordFactory,
    ExpiringRecordFactory,
    FamilyRequirementFactory,
    RequirementFactory,
    RequirementRecordFactory,
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

    def test_expired(self):
        expired = self.make(ExpiredRecordFactory)
        self.make(ExpiringRecordFactory)

        self.assertEqual(list(RequirementRecord.objects.expired()), [expired])

    def test_expiring_excludes_already_expired(self):
        self.make(ExpiredRecordFactory)
        expiring = self.make(ExpiringRecordFactory)

        self.assertEqual(list(RequirementRecord.objects.expiring()), [expiring])

    def test_expiring_respects_the_window(self):
        self.make(
            status=RequirementRecord.Status.COMPLETE,
            expires_on=timezone.localdate() + timezone.timedelta(days=45),
        )

        self.assertEqual(RequirementRecord.objects.expiring(within_days=30).count(), 0)
        self.assertEqual(RequirementRecord.objects.expiring(within_days=60).count(), 1)

    def test_complete_excludes_expired(self):
        self.make(ExpiredRecordFactory)
        current = self.make(status=RequirementRecord.Status.COMPLETE, expires_on=None)

        self.assertEqual(list(RequirementRecord.objects.complete()), [current])

    def test_needs_attention_gathers_everything_to_chase(self):
        outstanding = self.make()
        expired = self.make(ExpiredRecordFactory)
        expiring = self.make(ExpiringRecordFactory)
        self.make(status=RequirementRecord.Status.COMPLETE, expires_on=None)
        self.make(status=RequirementRecord.Status.WAIVED)

        self.assertEqual(
            set(RequirementRecord.objects.needs_attention()),
            {outstanding, expired, expiring},
        )

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
