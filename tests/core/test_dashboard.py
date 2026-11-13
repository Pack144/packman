from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from packman.calendars.factories import EventFactory, PackYearFactory
from packman.calendars.models import Event, PackYear
from packman.dens.factories import DenFactory, MembershipFactory
from packman.dens.models import Den, Membership, Rank
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory
from packman.membership.models import Adult, Family, Scout


@override_settings(TIME_ZONE="America/Los_Angeles")
class PackDashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        PackYear.objects.all().delete()
        self.now = datetime(2026, 3, 1, 12, tzinfo=ZoneInfo("America/Los_Angeles"))
        self.enterContext(patch("packman.core.dashboard.timezone.now", return_value=self.now))
        self.year = PackYearFactory(year=2026, start_date=date(2025, 9, 1), end_date=date(2026, 8, 31))
        self.previous_year = PackYearFactory(year=2025, start_date=date(2024, 9, 1), end_date=date(2025, 8, 31))
        self.user = AdultFactory(_is_staff=True, is_superuser=True)
        self.client.force_login(self.user)
        lion = Rank.objects.create(rank=Rank.RankChoices.LION)
        self.den = DenFactory(number=1, rank=lion)
        self.other_den = DenFactory(number=2)
        self.family = FamilyFactory()
        self.cubs = [
            ScoutFactory(family=self.family),
            ScoutFactory(family=self.family),
            ScoutFactory(),
        ]
        for cub in self.cubs[:2]:
            MembershipFactory(scout=cub, den=self.den, year_assigned=self.year)
        MembershipFactory(scout=self.cubs[2], den=self.other_den, year_assigned=self.year)
        MembershipFactory(scout=self.cubs[0], den=self.other_den, year_assigned=self.previous_year)
        self.adults = [
            AdultFactory(family=self.family),
            AdultFactory(family=self.family, is_active=False),
            AdultFactory(family=self.cubs[2].family),
        ]
        mixed_family = FamilyFactory()
        inactive = ScoutFactory(status=Scout.INACTIVE, family=mixed_family)
        MembershipFactory(scout=inactive, den=self.den, year_assigned=self.year)
        ScoutFactory(family=mixed_family)
        AdultFactory(family=mixed_family)
        MembershipFactory(year_assigned=self.previous_year, den=self.den)

    def dashboard(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        return response

    def assert_changelist(self, url, expected):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.context["cl"].queryset.values_list("pk", flat=True)), set(expected))

    def test_counts_and_membership_links(self):
        response = self.dashboard()
        self.assertEqual(response.context["pack_year"], self.year)
        self.assertContains(response, reverse("admin:calendars_packyear_change", args=[self.year.pk]))
        cards = response.context["dashboard_cards"]
        self.assertEqual([card["value"] for card in cards], [3, 3, 2, 0])
        self.assert_changelist(cards[0]["url"], [cub.pk for cub in self.cubs])
        self.assert_changelist(cards[1]["url"], [adult.pk for adult in self.adults])
        self.assert_changelist(cards[2]["url"], [self.family.pk, self.cubs[2].family_id])
        self.assertTemplateNotUsed(response, "unfold/helpers/dashboard_default.html")
        self.assertTemplateNotUsed(response, "admin/app_list.html")

    def test_den_table_matches_current_year_total_and_links(self):
        response = self.dashboard()
        rows = response.context["den_rows"]
        self.assertEqual({str(row["name"]): row["count"] for row in rows}, {"Den 1": 2, "Den 2": 1})
        self.assertEqual(sum(row["count"] for row in rows), response.context["cub_total"])
        self.assertContains(response, "Cubs by Den")
        self.assertNotContains(response, "Total Cubs")
        den_row = next(row for row in rows if str(row["name"]) == "Den 1")
        self.assertEqual(str(den_row["rank"]), "Lion")
        self.assertEqual(den_row["url"], reverse("admin:dens_den_change", args=[self.den.pk]))
        self.assert_changelist(den_row["cubs_url"], [cub.pk for cub in self.cubs[:2]])
        self.assertContains(response, "No rank assigned")

    def test_den_table_sorts_by_den_number_not_rank(self):
        lion = self.den.rank
        webelos = Rank.objects.create(rank=Rank.RankChoices.WEBE)
        self.den.rank = webelos
        self.den.save()
        self.other_den.rank = lion
        self.other_den.save()

        rows = self.dashboard().context["den_rows"]

        self.assertEqual([row["name"] for row in rows], ["Den 1", "Den 2"])
        self.assertEqual([str(row["rank"]) for row in rows], ["Webelos", "Lion"])

    def test_remaining_events_and_link_use_pack_year_and_local_dates(self):
        last_day = datetime(2026, 8, 31, 23, 59, tzinfo=ZoneInfo("America/Los_Angeles"))
        expected = [
            EventFactory(start=self.now, end=self.now + timedelta(hours=1)),
            EventFactory(start=self.now + timedelta(days=1), status=Event.TENTATIVE),
            EventFactory(start=last_day, end=last_day + timedelta(hours=1), published=False),
        ]
        EventFactory(start=self.now - timedelta(seconds=1))
        EventFactory(start=self.now + timedelta(days=1), status=Event.CANCELLED)
        EventFactory(start=last_day + timedelta(minutes=1))
        response = self.dashboard()
        card = response.context["dashboard_cards"][-1]
        self.assertEqual(str(card["title"]), "Remaining Events")
        self.assertEqual(card["value"], 3)
        self.assert_changelist(card["url"], [event.pk for event in expected])

    def test_staff_without_model_permissions_gets_no_statistics(self):
        self.user.is_superuser = False
        self.user.save()
        response = self.dashboard()
        self.assertEqual(response.context["dashboard_cards"], [])
        self.assertEqual(response.context["den_rows"], [])
        self.assertNotContains(response, "Cubs by Den")
        self.assertIsNone(response.context["pack_year_url"])
        self.assertContains(response, "You do not have permission to view pack statistics.")

    def test_cub_view_permission_shows_only_cubs_and_no_den_edit_links(self):
        self.user.is_superuser = False
        self.user.save()
        self.user.user_permissions.add(Permission.objects.get(codename="view_scout"))
        response = self.dashboard()
        self.assertEqual([str(card["title"]) for card in response.context["dashboard_cards"]], ["Cubs"])
        self.assertEqual(response.context["cub_total"], 3)
        self.assertTrue(all(row["url"] is None for row in response.context["den_rows"]))
        self.assert_changelist(response.context["dashboard_cards"][0]["url"], [cub.pk for cub in self.cubs])

    def test_change_permission_without_explicit_view_permission(self):
        self.user.is_superuser = False
        self.user.save()
        self.user.user_permissions.add(Permission.objects.get(codename="change_scout"))
        self.assertEqual(self.dashboard().context["cub_total"], 3)

    def test_each_card_respects_its_admin_queryset(self):
        for model, index, excluded in (
            (Scout, 0, self.cubs[0]),
            (Adult, 1, self.adults[0]),
            (Family, 2, self.family),
        ):
            with self.subTest(model=model):
                model_admin = admin.site.get_model_admin(model)
                original = model_admin.get_queryset
                with patch.object(
                    model_admin, "get_queryset", side_effect=lambda request: original(request).exclude(pk=excluded.pk)
                ):
                    response = self.dashboard()
                    card = response.context["dashboard_cards"][index]
                    expected = original(response.wsgi_request).exclude(pk=excluded.pk).active_in(self.year)
                    self.assertEqual(card["value"], expected.count())
                    self.assert_changelist(card["url"], expected.values_list("pk", flat=True))
                    if model is Scout:
                        self.assertEqual(sum(row["count"] for row in response.context["den_rows"]), 2)

    def test_event_card_respects_admin_queryset(self):
        included = EventFactory(start=self.now + timedelta(days=1))
        excluded = EventFactory(start=self.now + timedelta(days=2))
        model_admin = admin.site.get_model_admin(Event)
        original = model_admin.get_queryset
        with patch.object(
            model_admin, "get_queryset", side_effect=lambda request: original(request).exclude(pk=excluded.pk)
        ):
            card = self.dashboard().context["dashboard_cards"][-1]
            self.assertEqual(card["value"], 1)
            self.assert_changelist(card["url"], [included.pk])

    def test_den_and_pack_year_links_respect_admin_queryset(self):
        for model, context_key in ((Den, "den_rows"), (PackYear, "pack_year_url")):
            with self.subTest(model=model):
                model_admin = admin.site.get_model_admin(model)
                with patch.object(model_admin, "get_queryset", return_value=model.objects.none()):
                    response = self.dashboard()
                    if model is Den:
                        self.assertTrue(all(row["url"] is None for row in response.context[context_key]))
                    else:
                        self.assertIsNone(response.context[context_key])

    def test_module_permission_is_respected(self):
        with patch.object(admin.site.get_model_admin(Scout), "has_module_permission", return_value=False):
            response = self.dashboard()
        self.assertIsNone(response.context["cub_total"])
        self.assertEqual(len(response.context["dashboard_cards"]), 3)

    def test_empty_year_has_zero_totals_and_an_explicit_empty_table(self):
        Membership.objects.filter(year_assigned=self.year).delete()
        response = self.dashboard()
        self.assertEqual([card["value"] for card in response.context["dashboard_cards"]], [0, 0, 0, 0])
        self.assertContains(response, "No active Cubs have a den assignment in this Pack Year.")
        self.assertContains(response, "Cubs by Den")
        self.assertNotContains(response, "Total Cubs")

    def test_no_current_year_has_guidance_instead_of_misleading_zeros(self):
        self.year.delete()
        response = self.dashboard()
        self.assertIsNone(response.context["pack_year"])
        self.assertEqual(response.context["dashboard_cards"], [])
        self.assertContains(response, "No Pack Year covers today.")
        self.assertContains(response, reverse("admin:calendars_packyear_changelist"))

    def test_overlapping_years_have_explicit_guidance(self):
        PackYear.objects.create(year=2027, start_date=self.year.start_date, end_date=self.year.end_date)
        response = self.dashboard()
        self.assertIsNone(response.context["pack_year"])
        self.assertContains(response, "More than one Pack Year covers today.")
        self.assertEqual(response.context["dashboard_cards"], [])

    def test_year_selection_uses_local_date_and_ignores_stale_cache(self):
        cache.set("current_year", self.previous_year)
        just_before_midnight = datetime(2026, 8, 31, 23, 59, tzinfo=ZoneInfo("America/Los_Angeles"))
        with patch(
            "packman.core.dashboard.timezone.now", return_value=just_before_midnight.astimezone(ZoneInfo("UTC"))
        ):
            self.client.force_login(self.user)
            response = self.dashboard()
        self.assertEqual(response.context["pack_year"], self.year)

    def test_explicit_year_filter_uses_that_year_for_den_and_rank(self):
        params = {"active_in": self.previous_year.pk, "den": self.other_den.pk}
        url = reverse("admin:membership_scout_changelist", query=params)
        expected = [self.cubs[0].pk]
        self.assert_changelist(url, expected)
        self.other_den.rank = self.den.rank
        self.other_den.save()
        historical_cubs = list(Scout.objects.in_den(self.den, self.previous_year).values_list("pk", flat=True))
        url = reverse(
            "admin:membership_scout_changelist",
            query={"active_in": self.previous_year.pk, "rank": Rank.RankChoices.LION},
        )
        self.assert_changelist(url, expected + historical_cubs)

    def test_invalid_year_filter_uses_standard_admin_error_handling(self):
        for model in ("scout", "adult", "family"):
            for value in ("not-a-year", "9999"):
                with self.subTest(model=model, value=value):
                    url = reverse(f"admin:membership_{model}_changelist")
                    response = self.client.get(url, {"active_in": value})
                    self.assertRedirects(response, f"{url}?e=1")
