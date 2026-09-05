import datetime

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.compliance.scouting_membership import RENEWAL_WINDOW, Standing, standing_for, summarize_active_cubs
from packman.dens.factories import MembershipFactory
from packman.membership.factories import ActiveScoutFactory, ScoutFactory
from packman.membership.models import Scout

TODAY = timezone.localdate()
YESTERDAY = TODAY - datetime.timedelta(days=1)
TOMORROW = TODAY + datetime.timedelta(days=1)

# Every combination of the two fields, and what the rule says about each.
CASES = [
    ("nothing on file", "", None, Standing.MISSING),
    ("an ID but no expiration date", "12345678", None, Standing.MISSING),
    ("an expiration date but no ID", "", TOMORROW, Standing.MISSING),
    ("a past expiration date but no ID", "", YESTERDAY, Standing.MISSING),
    ("a registration expiring tomorrow", "12345678", TOMORROW, Standing.CURRENT),
    ("a registration expiring today", "12345678", TODAY, Standing.CURRENT),
    ("a registration that lapsed yesterday", "12345678", YESTERDAY, Standing.EXPIRED),
]


class StandingForTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_every_combination_of_the_two_fields(self):
        for label, membership_id, expires_on, expected in CASES:
            with self.subTest(label):
                cub = ScoutFactory.build(
                    scouting_membership_id=membership_id,
                    scouting_membership_expires_on=expires_on,
                )

                self.assertEqual(standing_for(cub), expected)

    def test_the_expiration_date_is_the_last_day_it_counts(self):
        cub = ScoutFactory.build(scouting_membership_id="12345678", scouting_membership_expires_on=TODAY)

        self.assertEqual(standing_for(cub), Standing.CURRENT)
        self.assertEqual(standing_for(cub, as_of=TOMORROW), Standing.EXPIRED)

    def test_as_of_lets_the_caller_ask_about_another_day(self):
        expires_on = TODAY + datetime.timedelta(days=30)
        cub = ScoutFactory.build(scouting_membership_id="12345678", scouting_membership_expires_on=expires_on)

        self.assertEqual(standing_for(cub, as_of=expires_on), Standing.CURRENT)
        self.assertEqual(standing_for(cub, as_of=expires_on + datetime.timedelta(days=1)), Standing.EXPIRED)

    def test_without_warn_within_a_soon_to_lapse_registration_is_still_current(self):
        """The default caller (the dashboard) only asks whether it is good today."""
        cub = ScoutFactory.build(
            scouting_membership_id="12345678",
            scouting_membership_expires_on=TODAY + datetime.timedelta(days=1),
        )

        self.assertEqual(standing_for(cub), Standing.CURRENT)

    def test_warn_within_flags_a_registration_that_lapses_inside_the_window(self):
        def standing(days_out):
            cub = ScoutFactory.build(
                scouting_membership_id="12345678",
                scouting_membership_expires_on=TODAY + datetime.timedelta(days=days_out),
            )
            return standing_for(cub, warn_within=RENEWAL_WINDOW)

        self.assertEqual(standing(90), Standing.CURRENT)
        self.assertEqual(standing(30), Standing.EXPIRING_SOON)
        self.assertEqual(standing(0), Standing.EXPIRING_SOON)
        self.assertEqual(standing(-1), Standing.EXPIRED)

    def test_warn_within_still_needs_both_fields_on_file(self):
        cub = ScoutFactory.build(scouting_membership_id="", scouting_membership_expires_on=TOMORROW)

        self.assertEqual(standing_for(cub, warn_within=RENEWAL_WINDOW), Standing.MISSING)


class SummarizeActiveCubsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()

    def setUp(self):
        cache.clear()

    def cub(self, membership_id="", expires_on=None, **kwargs):
        return ActiveScoutFactory(
            scouting_membership_id=membership_id,
            scouting_membership_expires_on=expires_on,
            **kwargs,
        )

    def test_counts_split_across_the_three_standings(self):
        self.cub("12345678", TOMORROW)
        self.cub("12345678", TOMORROW)
        self.cub("87654321", YESTERDAY)
        self.cub()

        summary = summarize_active_cubs(self.year)

        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["current"], 2)
        self.assertEqual(summary["expired"], 1)
        self.assertEqual(summary["missing"], 1)

    def test_outstanding_is_expired_plus_missing(self):
        self.cub("12345678", TOMORROW)
        self.cub("87654321", YESTERDAY)
        self.cub()

        summary = summarize_active_cubs(self.year)

        self.assertEqual(summary["outstanding"], 2)
        self.assertEqual(summary["current"] + summary["outstanding"], summary["total"])

    def test_rows_carry_the_cub_and_its_standing(self):
        cub = self.cub("12345678", YESTERDAY)

        summary = summarize_active_cubs(self.year)

        self.assertEqual(summary["rows"], [{"cub": cub, "standing": Standing.EXPIRED}])

    def test_only_active_cubs_are_asked(self):
        """Withdrawn and graduated Cubs are not expected to hold a registration."""
        self.cub("12345678", TOMORROW)
        MembershipFactory(scout=ScoutFactory(status=Scout.WITHDRAWN), year_assigned=self.year)
        MembershipFactory(scout=ScoutFactory(status=Scout.GRADUATED), year_assigned=self.year)

        summary = summarize_active_cubs(self.year)

        self.assertEqual(summary["total"], 1)

    def test_cubs_active_in_another_year_are_not_counted(self):
        other = PackYearFactory(year=self.year.year - 1)
        MembershipFactory(scout=ScoutFactory(status=Scout.ACTIVE), year_assigned=other)

        self.assertEqual(summarize_active_cubs(self.year)["total"], 0)
        self.assertEqual(summarize_active_cubs(other)["total"], 1)

    def test_no_active_cubs(self):
        summary = summarize_active_cubs(self.year)

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["rows"], [])
        self.assertEqual(summary["outstanding"], 0)

    def test_rows_are_ordered_by_name(self):
        self.cub(first_name="Zoe", last_name="Zebra")
        self.cub(first_name="Amy", last_name="Aardvark")

        summary = summarize_active_cubs(self.year)

        self.assertEqual([row["cub"].last_name for row in summary["rows"]], ["Aardvark", "Zebra"])
