from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.compliance.factories import (
    AdultRequirementFactory,
    CubRequirementFactory,
    FamilyRequirementFactory,
    RequirementRecordFactory,
)
from packman.compliance.models import Requirement, RequirementRecord
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory


class RequirementTestCase(TestCase):
    def test_string(self):
        self.assertEqual(str(CubRequirementFactory(name="Pack Dues")), "Pack Dues")

    def test_duration_requires_expiration(self):
        requirement = CubRequirementFactory.build(tracks_expiration=False, default_duration_days=365)

        with self.assertRaises(ValidationError) as ctx:
            requirement.clean()

        self.assertIn("default_duration_days", ctx.exception.message_dict)

    def test_tracks_member(self):
        self.assertTrue(CubRequirementFactory().tracks_member)
        self.assertTrue(AdultRequirementFactory().tracks_member)
        self.assertFalse(FamilyRequirementFactory().tracks_member)


class RequirementRecordConstraintTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.requirement = CubRequirementFactory()
        cls.family_requirement = FamilyRequirementFactory()

    def setUp(self):
        cache.clear()

    def test_one_record_per_member_per_requirement_per_year(self):
        scout = ActiveScoutFactory()
        RequirementRecord.objects.create(requirement=self.requirement, year=self.year, member=scout)

        with self.assertRaises(IntegrityError):
            RequirementRecord.objects.create(requirement=self.requirement, year=self.year, member=scout)

    def test_one_record_per_family_per_requirement_per_year(self):
        family = FamilyFactory()
        RequirementRecord.objects.create(requirement=self.family_requirement, year=self.year, family=family)

        with self.assertRaises(IntegrityError):
            RequirementRecord.objects.create(requirement=self.family_requirement, year=self.year, family=family)

    def test_same_member_may_repeat_in_a_later_year(self):
        scout = ActiveScoutFactory()
        next_year = CurrentPackYearFactory(year=self.year.year + 1)

        RequirementRecord.objects.create(requirement=self.requirement, year=self.year, member=scout)
        RequirementRecord.objects.create(requirement=self.requirement, year=next_year, member=scout)

        self.assertEqual(RequirementRecord.objects.filter(member=scout).count(), 2)

    def test_member_records_do_not_collide_across_families(self):
        """The family unique constraint must not fire for member-scoped records."""
        family = FamilyFactory()
        first = ActiveScoutFactory(family=family)
        second = ActiveScoutFactory(family=family)

        RequirementRecord.objects.create(requirement=self.requirement, year=self.year, member=first)
        RequirementRecord.objects.create(requirement=self.requirement, year=self.year, member=second)

        self.assertEqual(RequirementRecord.objects.filter(family=family).count(), 2)

    def test_record_must_have_a_subject(self):
        with self.assertRaises(IntegrityError):
            RequirementRecord.objects.create(requirement=self.requirement, year=self.year)


class RequirementRecordCleanTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()

    def setUp(self):
        cache.clear()

    def test_cub_requirement_rejects_an_adult(self):
        record = RequirementRecord(requirement=CubRequirementFactory(), year=self.year, member=AdultFactory())

        with self.assertRaises(ValidationError) as ctx:
            record.clean()

        self.assertIn("member", ctx.exception.message_dict)

    def test_adult_requirement_rejects_a_cub(self):
        record = RequirementRecord(requirement=AdultRequirementFactory(), year=self.year, member=ActiveScoutFactory())

        with self.assertRaises(ValidationError) as ctx:
            record.clean()

        self.assertIn("member", ctx.exception.message_dict)

    def test_family_requirement_rejects_a_member(self):
        record = RequirementRecord(requirement=FamilyRequirementFactory(), year=self.year, member=ActiveScoutFactory())

        with self.assertRaises(ValidationError) as ctx:
            record.clean()

        self.assertIn("member", ctx.exception.message_dict)

    def test_matching_audiences_are_accepted(self):
        for requirement, member in (
            (CubRequirementFactory(), ActiveScoutFactory()),
            (AdultRequirementFactory(), AdultFactory()),
        ):
            with self.subTest(audience=requirement.applies_to):
                RequirementRecord(requirement=requirement, year=self.year, member=member).clean()

    def test_expiration_cannot_precede_completion(self):
        today = timezone.localdate()
        record = RequirementRecord(
            requirement=CubRequirementFactory(),
            year=self.year,
            member=ActiveScoutFactory(),
            status=RequirementRecord.Status.COMPLETE,
            completed_on=today,
            expires_on=today - timezone.timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as ctx:
            record.clean()

        self.assertIn("expires_on", ctx.exception.message_dict)


class RequirementRecordFamilyBackfillTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()

    def setUp(self):
        cache.clear()

    def test_family_is_backfilled_from_a_scout(self):
        family = FamilyFactory()
        scout = ActiveScoutFactory(family=family)

        record = RequirementRecord.objects.create(requirement=CubRequirementFactory(), year=self.year, member=scout)

        self.assertEqual(record.family, family)

    def test_family_is_backfilled_from_an_adult(self):
        family = FamilyFactory()
        adult = AdultFactory(family=family)

        record = RequirementRecord.objects.create(requirement=AdultRequirementFactory(), year=self.year, member=adult)

        self.assertEqual(record.family, family)

    def test_explicit_family_is_not_overwritten(self):
        scout = ActiveScoutFactory()
        other = FamilyFactory()

        record = RequirementRecord.objects.create(
            requirement=CubRequirementFactory(), year=self.year, member=scout, family=other
        )

        self.assertEqual(record.family, other)

    def test_member_without_a_family_is_allowed(self):
        adult = AdultFactory(family=None)

        record = RequirementRecord.objects.create(requirement=AdultRequirementFactory(), year=self.year, member=adult)

        self.assertIsNone(record.family)


class EffectiveStatusTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.today = timezone.localdate()

    def setUp(self):
        cache.clear()

    def build(self, **kwargs):
        return RequirementRecordFactory.build(requirement=CubRequirementFactory(), year=self.year, **kwargs)

    def test_not_started(self):
        record = self.build(status=RequirementRecord.Status.NOT_STARTED)

        self.assertEqual(record.effective_status, RequirementRecord.Health.NOT_STARTED)
        self.assertFalse(record.is_satisfied)

    def test_waived(self):
        record = self.build(status=RequirementRecord.Status.WAIVED)

        self.assertEqual(record.effective_status, RequirementRecord.Health.WAIVED)
        self.assertTrue(record.is_satisfied)

    def test_complete_without_an_expiration(self):
        record = self.build(status=RequirementRecord.Status.COMPLETE, expires_on=None)

        self.assertEqual(record.effective_status, RequirementRecord.Health.COMPLETE)

    def test_expiration_boundaries(self):
        cases = (
            (-1, RequirementRecord.Health.EXPIRED),
            (0, RequirementRecord.Health.EXPIRING),
            (59, RequirementRecord.Health.EXPIRING),
            (60, RequirementRecord.Health.EXPIRING),
            (61, RequirementRecord.Health.COMPLETE),
        )
        for offset, expected in cases:
            with self.subTest(days=offset):
                record = self.build(
                    status=RequirementRecord.Status.COMPLETE,
                    expires_on=self.today + timezone.timedelta(days=offset),
                )
                self.assertEqual(record.effective_status, expected)

    def test_expired_is_not_satisfied(self):
        record = self.build(
            status=RequirementRecord.Status.COMPLETE,
            expires_on=self.today - timezone.timedelta(days=1),
        )

        self.assertFalse(record.is_satisfied)

    def test_pending_expiration_is_still_satisfied(self):
        record = self.build(
            status=RequirementRecord.Status.COMPLETE,
            expires_on=self.today + timezone.timedelta(days=30),
        )

        self.assertTrue(record.is_satisfied)


class RequirementRecordStringTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_string_names_the_subject_and_requirement(self):
        year = CurrentPackYearFactory()
        scout = ActiveScoutFactory(first_name="Test", last_name="Cub")
        requirement = CubRequirementFactory(name="Medical Form")

        record = RequirementRecord.objects.create(requirement=requirement, year=year, member=scout)

        self.assertIn("Test Cub", str(record))
        self.assertIn("Medical Form", str(record))

    def test_subject_prefers_the_member(self):
        year = CurrentPackYearFactory()
        family = FamilyFactory()
        scout = ActiveScoutFactory(family=family)

        record = RequirementRecord.objects.create(requirement=CubRequirementFactory(), year=year, member=scout)

        # Refetched, the FK resolves to the parent Member row rather than the
        # Scout that was assigned, so compare identity by primary key.
        subject = RequirementRecord.objects.get(pk=record.pk).subject
        self.assertEqual(subject.pk, scout.pk)
        self.assertEqual(subject.pk, scout.member_ptr.pk)

    def test_subject_falls_back_to_the_family(self):
        year = CurrentPackYearFactory()
        family = FamilyFactory()

        record = RequirementRecord.objects.create(requirement=FamilyRequirementFactory(), year=year, family=family)

        self.assertEqual(record.subject, family)


class AudienceTestCase(TestCase):
    def test_audience_values(self):
        self.assertEqual(
            set(Requirement.Audience.values),
            {"CUB", "ADULT", "FAMILY"},
        )
