from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.compliance.factories import (
    CubRequirementFactory,
    FamilyRequirementFactory,
    RequirementRecordFactory,
)
from packman.compliance.models import Requirement, RequirementRecord
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory

User = get_user_model()


class AdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.year = CurrentPackYearFactory()
        cls.superuser = User.objects.create_superuser(email="admin@example.com", password="changeme123")  # nosec B106

    def setUp(self):
        cache.clear()
        self.client.force_login(self.superuser)


class RequirementAdminTestCase(AdminTestCase):
    def test_changelist_renders(self):
        CubRequirementFactory(slug="admin-cub")

        response = self.client.get(reverse("admin:compliance_requirement_changelist"))

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_sync_action_opens_records(self):
        requirement = CubRequirementFactory(slug="admin-sync")
        ActiveScoutFactory()

        self.client.post(
            reverse("admin:compliance_requirement_changelist"),
            {"action": "sync_records_current_year", "_selected_action": [str(requirement.pk)]},
            follow=True,
        )

        self.assertEqual(requirement.records.count(), 1)

    def test_sync_action_is_idempotent(self):
        requirement = CubRequirementFactory(slug="admin-sync-twice")
        ActiveScoutFactory()

        for _ in range(2):
            self.client.post(
                reverse("admin:compliance_requirement_changelist"),
                {"action": "sync_records_current_year", "_selected_action": [str(requirement.pk)]},
                follow=True,
            )

        self.assertEqual(requirement.records.count(), 1)


class RequirementRecordAdminTestCase(AdminTestCase):
    def test_changelist_renders(self):
        RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="admin-record"),
            year=self.year,
            member=ActiveScoutFactory(),
        )

        response = self.client.get(reverse("admin:compliance_requirementrecord_changelist"))

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_changelist_defaults_to_the_current_pack_year(self):
        requirement = CubRequirementFactory(slug="admin-year-filter")
        older = PackYearFactory(year=self.year.year - 3, follows_calendar=True)
        RequirementRecordFactory(requirement=requirement, year=self.year, member=ActiveScoutFactory())
        RequirementRecordFactory(requirement=requirement, year=older, member=ActiveScoutFactory())

        response = self.client.get(reverse("admin:compliance_requirementrecord_changelist"))

        shown = response.context["cl"].queryset
        self.assertEqual([record.year for record in shown], [self.year])

    def test_all_sentinel_shows_every_year(self):
        requirement = CubRequirementFactory(slug="admin-year-all")
        older = PackYearFactory(year=self.year.year - 3, follows_calendar=True)
        RequirementRecordFactory(requirement=requirement, year=self.year, member=ActiveScoutFactory())
        RequirementRecordFactory(requirement=requirement, year=older, member=ActiveScoutFactory())

        response = self.client.get(
            reverse("admin:compliance_requirementrecord_changelist"), {"year__year__exact": "all"}
        )

        self.assertEqual(response.context["cl"].queryset.count(), 2)

    def test_mark_complete_sets_the_date(self):
        requirement = CubRequirementFactory(slug="admin-complete")
        record = RequirementRecordFactory(requirement=requirement, year=self.year, member=ActiveScoutFactory())

        self.client.post(
            reverse("admin:compliance_requirementrecord_changelist"),
            {"action": "mark_complete", "_selected_action": [str(record.pk)]},
            follow=True,
        )

        record.refresh_from_db()
        self.assertEqual(record.status, RequirementRecord.Status.COMPLETE)
        self.assertEqual(record.completed_on, timezone.localdate())
        self.assertEqual(record.recorded_by, self.superuser)

    def test_mark_waived(self):
        record = RequirementRecordFactory(
            requirement=CubRequirementFactory(slug="admin-waive"),
            year=self.year,
            member=ActiveScoutFactory(),
        )

        self.client.post(
            reverse("admin:compliance_requirementrecord_changelist"),
            {"action": "mark_waived", "_selected_action": [str(record.pk)]},
            follow=True,
        )

        record.refresh_from_db()
        self.assertEqual(record.status, RequirementRecord.Status.WAIVED)


class InlineTestCase(AdminTestCase):
    """
    The payoff for pointing the foreign key at Member rather than at Scout and
    Adult separately: one inline serves both change pages.
    """

    def test_inline_renders_on_the_cub_page(self):
        scout = ActiveScoutFactory()

        response = self.client.get(reverse("admin:membership_scout_change", args=[scout.pk]))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Membership Requirements")

    def test_inline_renders_on_the_adult_page(self):
        adult = AdultFactory()

        response = self.client.get(reverse("admin:membership_adult_change", args=[adult.pk]))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Membership Requirements")

    def test_family_inline_shows_only_family_scoped_records(self):
        family = FamilyFactory()
        scout = ActiveScoutFactory(family=family)
        RequirementRecordFactory(requirement=CubRequirementFactory(slug="inline-cub"), year=self.year, member=scout)
        dues = RequirementRecordFactory(
            requirement=FamilyRequirementFactory(slug="inline-dues"),
            year=self.year,
            member=None,
            family=family,
        )

        response = self.client.get(reverse("admin:membership_family_change", args=[family.pk]))

        formset = next(fs for fs in response.context["inline_admin_formsets"] if fs.formset.model is RequirementRecord)
        self.assertEqual([form.instance.pk for form in formset.formset.forms if form.instance.pk], [dues.pk])


class MemberAdminTestCase(AdminTestCase):
    """Member is registered for lookup only so the record autocomplete works."""

    def test_changelist_renders(self):
        ActiveScoutFactory()

        response = self.client.get(reverse("admin:membership_member_changelist"))

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_autocomplete_finds_members(self):
        ActiveScoutFactory(first_name="Autocomplete", last_name="Target")

        response = self.client.get(
            reverse("admin:autocomplete"),
            {
                "app_label": "compliance",
                "model_name": "requirementrecord",
                "field_name": "member",
                "term": "Autocomplete",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_members_cannot_be_added_here(self):
        response = self.client.get(reverse("admin:membership_member_changelist"))

        self.assertNotContains(response, "Add member")


class RequirementCountAnnotationTestCase(AdminTestCase):
    def test_record_count_column_counts_only_the_current_year(self):
        requirement = CubRequirementFactory(slug="admin-count")
        older = PackYearFactory(year=self.year.year - 4, follows_calendar=True)
        RequirementRecordFactory(requirement=requirement, year=self.year, member=ActiveScoutFactory())
        RequirementRecordFactory(requirement=requirement, year=older, member=ActiveScoutFactory())

        response = self.client.get(reverse("admin:compliance_requirement_changelist"))

        shown = response.context["cl"].queryset.get(pk=requirement.pk)
        self.assertEqual(shown.record_count, 1)


class RequirementModelRegistrationTestCase(TestCase):
    def test_both_models_are_registered(self):
        from django.contrib import admin as django_admin

        self.assertIn(Requirement, django_admin.site._registry)
        self.assertIn(RequirementRecord, django_admin.site._registry)
