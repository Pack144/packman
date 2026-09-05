"""
The Scouting America membership rule, and the agreement between its two forms.

compliance/derived.py spells the rule out twice -- once in Python for a single
record, once as a Q for the dashboard's aggregates. Nothing but a test keeps
them saying the same thing, so that agreement is asserted directly here.
"""

import datetime

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.compliance.derived import (
    scouting_membership_expired,
    scouting_membership_q,
    scouting_membership_satisfied,
)
from packman.compliance.factories import (
    CubRequirementFactory,
    RequirementRecordFactory,
    ScoutingMembershipCubFactory,
)
from packman.compliance.models import RequirementRecord
from packman.membership.factories import ActiveScoutFactory
from packman.membership.models import Member

TODAY = timezone.localdate()
YESTERDAY = TODAY - datetime.timedelta(days=1)
TOMORROW = TODAY + datetime.timedelta(days=1)

# Every combination of the two fields, and what the rule says about each.
CASES = [
    ("nothing on file", "", None, RequirementRecord.Status.NOT_STARTED),
    ("an ID but no date", "12345678", None, RequirementRecord.Status.NOT_STARTED),
    ("a date but no ID", "", TOMORROW, RequirementRecord.Status.NOT_STARTED),
    ("a past date but no ID", "", YESTERDAY, RequirementRecord.Status.NOT_STARTED),
    ("a registration expiring tomorrow", "12345678", TOMORROW, RequirementRecord.Status.COMPLETE),
    ("a registration expiring today", "12345678", TODAY, RequirementRecord.Status.COMPLETE),
    ("a registration that lapsed yesterday", "12345678", YESTERDAY, RequirementRecord.Status.EXPIRED),
]


class ScoutingMembershipRuleTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_satisfied_and_expired_partition_the_cases(self):
        for label, membership_id, expires_on, expected in CASES:
            with self.subTest(label):
                member = ActiveScoutFactory(
                    scouting_membership_id=membership_id,
                    scouting_membership_expires_on=expires_on,
                )
                satisfied = scouting_membership_satisfied(member)
                expired = scouting_membership_expired(member)

                self.assertEqual(satisfied, expected == RequirementRecord.Status.COMPLETE)
                self.assertEqual(expired, expected == RequirementRecord.Status.EXPIRED)
                # Never both, which is what makes the three states a partition.
                self.assertFalse(satisfied and expired)

    def test_expires_today_still_counts(self):
        """The last day of a registration is a day it is still held."""
        member = ActiveScoutFactory(scouting_membership_id="12345678", scouting_membership_expires_on=TODAY)

        self.assertTrue(scouting_membership_satisfied(member))
        self.assertFalse(scouting_membership_expired(member))

    def test_a_missing_member_is_never_satisfied(self):
        """Family-scoped records carry no member; the rule must not blow up."""
        self.assertFalse(scouting_membership_satisfied(None))
        self.assertFalse(scouting_membership_expired(None))

    def test_python_and_sql_agree(self):
        for label, membership_id, expires_on, _expected in CASES:
            with self.subTest(label):
                member = ActiveScoutFactory(
                    scouting_membership_id=membership_id,
                    scouting_membership_expires_on=expires_on,
                )
                in_sql = Member.objects.filter(scouting_membership_q(), pk=member.pk).exists()
                expired_in_sql = Member.objects.filter(scouting_membership_q(expired=True), pk=member.pk).exists()

                self.assertEqual(in_sql, scouting_membership_satisfied(member))
                self.assertEqual(expired_in_sql, scouting_membership_expired(member))

    def test_a_whitespace_only_id_is_not_on_file(self):
        """
        Member.save() strips the ID so that "" means the same thing to the
        Python check and to the SQL one, which excludes "" exactly.
        """
        member = ActiveScoutFactory(scouting_membership_id="   ", scouting_membership_expires_on=TOMORROW)
        member.refresh_from_db()

        self.assertEqual(member.scouting_membership_id, "")
        self.assertFalse(scouting_membership_satisfied(member))
        self.assertFalse(Member.objects.filter(scouting_membership_q(), pk=member.pk).exists())


class EffectiveStatusTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.derived = ScoutingMembershipCubFactory(slug="sa-membership-cub")
        cls.manual = CubRequirementFactory(slug="manual-cub")

    def setUp(self):
        cache.clear()

    def record_for(self, requirement, **member_kwargs):
        return RequirementRecordFactory(
            requirement=requirement,
            year=self.year,
            member=ActiveScoutFactory(**member_kwargs),
        )

    def test_derived_records_read_off_the_member(self):
        for label, membership_id, expires_on, expected in CASES:
            with self.subTest(label):
                record = self.record_for(
                    self.derived,
                    scouting_membership_id=membership_id,
                    scouting_membership_expires_on=expires_on,
                )

                self.assertEqual(record.effective_status, expected)
                self.assertEqual(record.is_satisfied, expected == RequirementRecord.Status.COMPLETE)

    def test_a_derived_record_ignores_its_own_status_column(self):
        """Marking a lapsed registration complete by hand must not stick."""
        record = self.record_for(
            self.derived,
            scouting_membership_id="12345678",
            scouting_membership_expires_on=YESTERDAY,
        )
        record.status = RequirementRecord.Status.COMPLETE
        record.save()

        self.assertEqual(record.effective_status, RequirementRecord.Status.EXPIRED)
        self.assertFalse(record.is_satisfied)

    def test_waiving_outranks_the_members_own_fields(self):
        record = self.record_for(
            self.derived,
            scouting_membership_id="",
            scouting_membership_expires_on=None,
        )
        record.status = RequirementRecord.Status.WAIVED
        record.save()

        self.assertEqual(record.effective_status, RequirementRecord.Status.WAIVED)
        self.assertTrue(record.is_satisfied)

    def test_manual_records_are_untouched(self):
        record = self.record_for(
            self.manual,
            scouting_membership_id="",
            scouting_membership_expires_on=None,
        )
        record.status = RequirementRecord.Status.COMPLETE
        record.save()

        self.assertEqual(record.effective_status, RequirementRecord.Status.COMPLETE)
        self.assertTrue(record.is_satisfied)

    def test_nothing_manual_ever_expires(self):
        record = self.record_for(self.manual)

        self.assertNotEqual(record.effective_status, RequirementRecord.Status.EXPIRED)

    def test_display_label(self):
        record = self.record_for(
            self.derived,
            scouting_membership_id="12345678",
            scouting_membership_expires_on=YESTERDAY,
        )

        self.assertEqual(record.get_effective_status_display(), "Expired")
