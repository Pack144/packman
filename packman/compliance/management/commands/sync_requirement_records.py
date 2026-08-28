from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from packman.calendars.models import PackYear
from packman.compliance.models import Requirement


class Command(BaseCommand):
    help = "Open requirement records for every active Cub, adult, and family in a pack year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            help="The pack year to sync. Defaults to the current one.",
        )
        parser.add_argument(
            "--requirement",
            help="Sync a single requirement, given its slug. Defaults to every active requirement.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing anything.",
        )

    def handle(self, *args, **options):
        year = self.get_year(options["year"])
        requirements = self.get_requirements(options["requirement"])

        total = 0
        with transaction.atomic():
            for requirement in requirements:
                created = requirement.sync_records(year=year)
                total += len(created)
                self.stdout.write(f"  {requirement}: {len(created)} opened")

            if options["dry_run"]:
                transaction.set_rollback(True)

        summary = f"{total} record(s) opened for {year}"
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run, rolled back. Would have opened {summary}."))
        else:
            self.stdout.write(self.style.SUCCESS(summary.capitalize() + "."))

    def get_year(self, year):
        if year is None:
            try:
                return PackYear.objects.current()
            except PackYear.DoesNotExist:
                raise CommandError("No pack year covers today. Pass --year to choose one.") from None
        try:
            return PackYear.objects.get(year=year)
        except PackYear.DoesNotExist:
            raise CommandError(f"There is no pack year {year}.") from None

    def get_requirements(self, slug):
        requirements = Requirement.objects.active()
        if slug:
            requirements = requirements.filter(slug=slug)
            if not requirements.exists():
                raise CommandError(f"There is no active requirement with the slug {slug!r}.")
        return requirements
