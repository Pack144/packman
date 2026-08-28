from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from packman.calendars.factories import CurrentPackYearFactory
from packman.compliance.factories import CubRequirementFactory, FamilyRequirementFactory
from packman.compliance.models import RequirementRecord
from packman.membership.factories import ActiveScoutFactory, CompleteFamilyFactory


class SyncRequirementRecordsCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()

    def setUp(self):
        cache.clear()

    def records(self, slug):
        return RequirementRecord.objects.filter(requirement__slug=slug)

    def run_command(self, *args, **kwargs):
        out = StringIO()
        call_command("sync_requirement_records", *args, stdout=out, stderr=StringIO(), **kwargs)
        return out.getvalue()

    def test_opens_records_for_the_named_year(self):
        CubRequirementFactory(slug="cmd-cub")
        ActiveScoutFactory()

        self.run_command("--year", str(self.year.year))

        self.assertEqual(self.records("cmd-cub").count(), 1)

    def test_is_idempotent(self):
        CubRequirementFactory(slug="cmd-idempotent")
        ActiveScoutFactory()

        self.run_command("--year", str(self.year.year))
        self.run_command("--year", str(self.year.year))

        self.assertEqual(self.records("cmd-idempotent").count(), 1)

    def test_dry_run_writes_nothing(self):
        CubRequirementFactory(slug="cmd-dry")
        ActiveScoutFactory()

        output = self.run_command("--year", str(self.year.year), "--dry-run")

        self.assertEqual(RequirementRecord.objects.count(), 0)
        self.assertIn("Dry run", output)

    def test_can_target_a_single_requirement(self):
        CubRequirementFactory(slug="cmd-wanted")
        CubRequirementFactory(slug="cmd-skipped")
        ActiveScoutFactory()

        self.run_command("--year", str(self.year.year), "--requirement", "cmd-wanted")

        self.assertEqual(RequirementRecord.objects.count(), 1)
        self.assertEqual(RequirementRecord.objects.get().requirement.slug, "cmd-wanted")

    def test_skips_inactive_requirements(self):
        CubRequirementFactory(slug="cmd-retired", is_active=False)
        ActiveScoutFactory()

        self.run_command("--year", str(self.year.year))

        self.assertEqual(self.records("cmd-retired").count(), 0)

    def test_unknown_year_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_command("--year", "1899")

    def test_unknown_requirement_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_command("--year", str(self.year.year), "--requirement", "does-not-exist")

    def test_family_with_two_cubs_gets_one_dues_record(self):
        """The end-to-end guard against FamilyQuerySet.active() duplicating rows."""
        FamilyRequirementFactory(slug="cmd-dues")
        CompleteFamilyFactory(active_children=2)

        self.run_command("--year", str(self.year.year))

        self.assertEqual(self.records("cmd-dues").count(), 1)
