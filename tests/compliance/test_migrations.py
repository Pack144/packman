import importlib

from django.core.cache import cache
from django.test import TestCase

from packman.calendars.factories import CurrentPackYearFactory
from packman.compliance.models import Requirement, RequirementRecord
from packman.membership.factories import ActiveScoutFactory

SEEDED_SLUGS = {"bsa-membership", "medical-form-cub", "medical-form-adult", "pack-dues"}

seed = importlib.import_module("packman.compliance.migrations.0002_seed_default_requirements")


class SeedDefaultRequirementsTestCase(TestCase):
    """
    The seed migration has already run against the test database, so these
    assert the resulting state rather than replaying the migration.
    """

    def test_all_four_requirements_are_seeded(self):
        self.assertEqual(set(Requirement.objects.values_list("slug", flat=True)), SEEDED_SLUGS)

    def test_audiences(self):
        by_slug = {r.slug: r for r in Requirement.objects.all()}

        self.assertEqual(by_slug["bsa-membership"].applies_to, Requirement.Audience.CUB)
        self.assertEqual(by_slug["medical-form-cub"].applies_to, Requirement.Audience.CUB)
        self.assertEqual(by_slug["medical-form-adult"].applies_to, Requirement.Audience.ADULT)
        self.assertEqual(by_slug["pack-dues"].applies_to, Requirement.Audience.FAMILY)

    def test_only_dues_does_not_expire(self):
        self.assertFalse(Requirement.objects.get(slug="pack-dues").tracks_expiration)
        self.assertFalse(Requirement.objects.exclude(slug="pack-dues").filter(tracks_expiration=False).exists())

    def test_medical_forms_are_separate_per_audience(self):
        """Cub and adult medical forms are distinct requirements, not one multi-audience type."""
        medical = Requirement.objects.filter(slug__startswith="medical-form")

        self.assertEqual(medical.count(), 2)
        self.assertEqual({r.applies_to for r in medical}, {Requirement.Audience.CUB, Requirement.Audience.ADULT})

    def test_seeds_are_ordered_for_display(self):
        self.assertEqual(
            list(Requirement.objects.values_list("slug", flat=True)),
            ["bsa-membership", "medical-form-cub", "medical-form-adult", "pack-dues"],
        )

    def test_seed_is_idempotent(self):
        seed.create_default_requirements(FakeApps(), None)

        self.assertEqual(Requirement.objects.count(), len(SEEDED_SLUGS))

    def test_seed_does_not_overwrite_local_edits(self):
        Requirement.objects.filter(slug="pack-dues").update(name="Pack Dues and Fees", sort_order=99)

        seed.create_default_requirements(FakeApps(), None)

        dues = Requirement.objects.get(slug="pack-dues")
        self.assertEqual(dues.name, "Pack Dues and Fees")
        self.assertEqual(dues.sort_order, 99)


class RemoveDefaultRequirementsTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_reverse_removes_unused_seeds(self):
        seed.remove_default_requirements(FakeApps(), None)

        self.assertFalse(Requirement.objects.filter(slug__in=SEEDED_SLUGS).exists())

    def test_reverse_spares_requirements_that_have_records(self):
        """Rolling back must never discard paperwork leadership already collected."""
        RequirementRecord.objects.create(
            requirement=Requirement.objects.get(slug="bsa-membership"),
            year=CurrentPackYearFactory(),
            member=ActiveScoutFactory(),
        )

        seed.remove_default_requirements(FakeApps(), None)

        self.assertTrue(Requirement.objects.filter(slug="bsa-membership").exists())
        self.assertFalse(Requirement.objects.filter(slug="pack-dues").exists())


class FakeApps:
    """
    Stands in for the migration state registry. The seed functions only ask for
    the Requirement model, and the real one is equivalent here.
    """

    @staticmethod
    def get_model(app_label, model_name):
        return {"requirement": Requirement, "requirementrecord": RequirementRecord}[model_name.lower()]
