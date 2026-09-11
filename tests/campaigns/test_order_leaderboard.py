import decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.campaigns.models import Campaign, Customer, Order
from packman.dens.factories import DenFactory
from packman.dens.models import Membership, Rank
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory


class OrderLeaderboardWeekFilterTest(TestCase):
    def setUp(self):
        self.pack_year = CurrentPackYearFactory()
        self.family = FamilyFactory()
        self.adult = AdultFactory(family=self.family, is_active=True)
        self.scout = ScoutFactory(family=self.family)
        rank = Rank.objects.create(rank=Rank.RankChoices.LION, description="Lion")
        Membership.objects.create(
            scout=self.scout,
            den=DenFactory(number=1, rank=rank),
            year_assigned=self.pack_year,
        )
        self.customer = Customer.objects.create(name="Test Customer")

        today = timezone.localdate()
        self.campaign_start = today - timezone.timedelta(days=16)
        self.now = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time())) + (
            timezone.timedelta(hours=12)
        )
        self.campaign = Campaign.objects.create(
            year=self.pack_year,
            ordering_opens=timezone.make_aware(
                timezone.datetime.combine(self.campaign_start, timezone.datetime.min.time())
            )
            + timezone.timedelta(hours=10),
            ordering_closes=self.now + timezone.timedelta(days=30),
            delivery_available=(self.now + timezone.timedelta(days=35)).date(),
            prize_window_opens=today,
            prize_window_closes=(self.now + timezone.timedelta(days=40)).date(),
        )
        self.client.force_login(self.adult)

    def create_order(self, donation, added_at, award_ineligible=None):
        order = Order.objects.create(
            campaign=self.campaign,
            seller=self.scout,
            customer=self.customer,
            recorded_by=self.adult,
            donation=decimal.Decimal(donation),
            award_ineligible=award_ineligible,
        )
        Order.objects.filter(pk=order.pk).update(date_added=added_at)
        return order

    def campaign_day(self, day, hour=12):
        date = self.campaign_start + timezone.timedelta(days=day)
        return timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time())) + (
            timezone.timedelta(hours=hour)
        )

    def get_leaderboard(self, week=None, campaign=None, current_time=None, **query):
        if week is not None:
            query["week"] = week
        url = reverse(
            "campaigns:order_leaderboard_by_campaign",
            kwargs={"campaign": campaign or self.pack_year.year},
        )
        with mock.patch("packman.campaigns.views.timezone.now", return_value=current_time or self.now):
            return self.client.get(url, query)

    def test_campaign_week_helpers_round_up_and_share_boundaries(self):
        self.assertEqual(self.campaign.get_ordering_week_count(), 7)

        weeks = self.campaign.get_ordering_week_windows(3)

        self.assertEqual([week["number"] for week in weeks], [1, 2, 3])
        self.assertEqual(set(weeks[0]), {"number", "start_at", "end_at"})
        self.assertEqual(weeks[0]["start_at"], timezone.localtime(self.campaign.ordering_opens))
        self.assertEqual(weeks[0]["end_at"], weeks[1]["start_at"])
        self.assertEqual(weeks[1]["end_at"], weeks[2]["start_at"])

    def test_dropdown_lists_all_time_then_weeks_in_campaign_order(self):
        self.create_order("100.00", self.campaign_day(2))

        response = self.get_leaderboard()

        self.assertEqual([week["number"] for week in response.context["leaderboard_weeks"]], [1, 2, 3])
        self.assertIsNone(response.context["selected_leaderboard_week"])
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, "NCC Leaderboards")
        self.assertContains(response, '<option value="" selected>Full Campaign</option>', html=True)
        self.assertContains(response, 'data-bs-toggle="tab"', count=4)
        self.assertContains(response, 'class="tab-pane fade show active"', count=1)
        self.assertContains(response, 'class="tab-pane fade', count=4)
        self.assertContains(response, "table table-hover align-middle sortable", count=2)
        self.assertContains(response, 'class="table table-hover align-middle"', count=2)
        self.assertContains(response, "leaderboard-row-label", count=4)
        self.assertNotContains(response, "<caption")
        self.assertEqual(response.context["top_sellers"][0]["scout"], self.scout)
        self.assertContains(response, f'id="{self.scout.slug}_thumbnail"', count=3)
        self.assertContains(response, 'src="/static/img/lion.png"', count=1)
        self.assertContains(response, "Golden Peanut")
        self.assertContains(response, 'name="tab" value="top-sales"', count=1)
        self.assertContains(
            response,
            reverse("campaigns:order_leaderboard"),
        )

        content = response.content.decode()
        self.assertLess(content.index("Full Campaign"), content.index("Week 1"))
        self.assertLess(content.index("Week 1"), content.index("Week 2"))
        self.assertLess(content.index("Week 2"), content.index("Week 3"))

    def test_hidden_week_shows_countdown_until_midnight_after_it_ends(self):
        self.create_order("100.00", self.campaign_day(2))
        self.create_order("200.00", self.campaign_day(9))
        reveal_midnight = self.campaign_day(15, hour=0)

        before_reveal = self.get_leaderboard(
            2,
            current_time=reveal_midnight - timezone.timedelta(microseconds=1),
        )

        self.assertEqual([week["number"] for week in before_reveal.context["leaderboard_weeks"]], [1, 2, 3])
        self.assertEqual(before_reveal.context["selected_leaderboard_week"]["number"], 2)
        self.assertEqual(before_reveal.context["week_reveal_at"], reveal_midnight)
        self.assertTrue(before_reveal.context["hide_leaderboard"])
        self.assertContains(before_reveal, "This week's orders closed")
        self.assertContains(before_reveal, "This week's leaderboard will be available in")
        self.assertNotContains(before_reveal, 'src="/static/img/golden_peanut.jpeg"')

        current_week = self.get_leaderboard(
            3,
            current_time=reveal_midnight - timezone.timedelta(microseconds=1),
        )

        self.assertEqual(current_week.context["selected_leaderboard_week"]["number"], 3)
        self.assertEqual(current_week.context["week_reveal_at"], self.campaign_day(22, hour=0))
        self.assertTrue(current_week.context["hide_leaderboard"])
        self.assertContains(current_week, "This week's orders close in")
        self.assertContains(current_week, "This week's leaderboard will be available in")

        at_reveal = self.get_leaderboard(2, current_time=reveal_midnight)

        self.assertEqual(at_reveal.context["selected_leaderboard_week"]["number"], 2)
        self.assertEqual(at_reveal.context["selected_leaderboard_week"]["end_at"], self.campaign_day(14, hour=10))
        self.assertEqual(set(at_reveal.context["selected_leaderboard_week"]), {"number", "start_at", "end_at"})
        self.assertEqual(at_reveal.context["top_sellers"][0]["total"], decimal.Decimal("200.00"))

    def test_final_week_extends_past_campaign_close_before_becoming_available(self):
        self.campaign.ordering_closes = self.campaign_day(16)
        self.campaign.save(update_fields=["ordering_closes"])
        self.create_order("700.00", self.campaign_day(15))
        final_week_reveal = self.campaign_day(22, hour=0)

        before_reveal = self.get_leaderboard(
            3,
            current_time=final_week_reveal - timezone.timedelta(microseconds=1),
        )

        self.assertEqual(before_reveal.status_code, 200)
        self.assertTrue(before_reveal.context["hide_leaderboard"])
        self.assertTrue(before_reveal.context["hide_week_selector"])
        self.assertEqual(before_reveal.context["campaign_end_at"], self.campaign_day(16))
        self.assertEqual(before_reveal.context["leaderboard_reveal_at"], final_week_reveal)
        self.assertContains(before_reveal, "Campaign orders closed")
        self.assertContains(before_reveal, "The leaderboard will be available again in")
        self.assertContains(before_reveal, 'src="/static/img/golden_peanut.jpeg"')

        at_reveal = self.get_leaderboard(3, current_time=final_week_reveal)

        self.assertEqual([week["number"] for week in at_reveal.context["leaderboard_weeks"]], [1, 2, 3])
        self.assertEqual(at_reveal.context["selected_leaderboard_week"]["end_at"], self.campaign_day(21, hour=10))
        self.assertEqual(at_reveal.context["top_sellers"][0]["total"], decimal.Decimal("700.00"))
        self.assertNotIn("hide_leaderboard", at_reveal.context)
        self.assertNotContains(at_reveal, 'src="/static/img/golden_peanut.jpeg"')

    def test_selected_week_filters_every_leaderboard_total(self):
        self.create_order("100.00", self.campaign_day(2))
        self.create_order("250.00", self.campaign_day(9))
        self.create_order("400.00", self.campaign_day(15))

        response = self.get_leaderboard(2)

        self.assertEqual(response.context["selected_leaderboard_week"]["number"], 2)
        self.assertContains(response, "Top Sellers")
        self.assertNotContains(response, "Golden Peanut")
        self.assertEqual(response.context["top_sellers"][0]["orders"], 1)
        self.assertEqual(response.context["top_sellers"][0]["total"], decimal.Decimal("250.00"))
        self.assertEqual(response.context["top_orders"][0]["orders"], 1)
        self.assertEqual(response.context["all_sellers"][0]["total"], decimal.Decimal("250.00"))
        self.assertEqual(response.context["dens"][0]["orders"], 1)
        self.assertEqual(response.context["dens"][0]["total"], decimal.Decimal("250.00"))

    def test_week_boundaries_use_campaign_opening_time_and_exclusive_end(self):
        self.create_order("100.00", self.campaign_day(7, 9))
        self.create_order("200.00", self.campaign_day(7, 10))

        first_week = self.get_leaderboard(1)
        second_week = self.get_leaderboard(2)

        self.assertEqual(first_week.context["top_sellers"][0]["total"], decimal.Decimal("100.00"))
        self.assertEqual(second_week.context["top_sellers"][0]["total"], decimal.Decimal("200.00"))

    def test_invalid_or_unavailable_week_returns_not_found(self):
        self.create_order("100.00", self.campaign_day(2))
        self.create_order("200.00", self.campaign_day(9))

        for week in ("not-a-week", 4):
            with self.subTest(week=week):
                response = self.get_leaderboard(week)

                self.assertEqual(response.status_code, 404)

    def test_week_filter_still_excludes_award_ineligible_orders(self):
        self.create_order("100.00", self.campaign_day(9))
        self.create_order("900.00", self.campaign_day(9), award_ineligible=True)

        response = self.get_leaderboard(2)

        self.assertEqual(response.context["top_sellers"][0]["orders"], 1)
        self.assertEqual(response.context["top_sellers"][0]["total"], decimal.Decimal("100.00"))

    def test_campaign_dropdown_opens_a_past_campaign_leaderboard(self):
        past_year = PackYearFactory(year=self.pack_year.year - 1)
        past_start = self.campaign_start - timezone.timedelta(days=365)
        past_campaign = Campaign.objects.create(
            year=past_year,
            ordering_opens=timezone.make_aware(timezone.datetime.combine(past_start, timezone.datetime.min.time())),
            ordering_closes=timezone.make_aware(
                timezone.datetime.combine(past_start + timezone.timedelta(days=28), timezone.datetime.min.time())
            ),
            delivery_available=past_start + timezone.timedelta(days=35),
            prize_window_opens=past_start,
            prize_window_closes=past_start + timezone.timedelta(days=40),
        )
        current_membership = self.scout.den_memberships.get(year_assigned=self.pack_year)
        Membership.objects.create(scout=self.scout, den=current_membership.den, year_assigned=past_year)
        past_order = Order.objects.create(
            campaign=past_campaign,
            seller=self.scout,
            customer=self.customer,
            recorded_by=self.adult,
            donation=decimal.Decimal("325.00"),
        )
        Order.objects.filter(pk=past_order.pk).update(
            date_added=timezone.make_aware(
                timezone.datetime.combine(past_start + timezone.timedelta(days=2), timezone.datetime.min.time())
            )
        )
        url = reverse("campaigns:order_leaderboard_by_campaign", args=[past_year.year])

        response = self.client.get(url)

        self.assertEqual(response.context["campaigns"]["viewing"], past_campaign)
        self.assertContains(response, str(past_campaign))
        self.assertContains(
            response,
            reverse("campaigns:order_leaderboard"),
        )
        self.assertFalse(response.context["show_den_rank_badges"])
        self.assertNotContains(response, 'src="/static/img/lion.png"')
        self.assertEqual(response.context["top_sellers"][0]["total"], decimal.Decimal("325.00"))

        weekly_response = self.client.get(url, {"week": 1})
        self.assertEqual(weekly_response.context["selected_leaderboard_week"]["number"], 1)
        self.assertEqual(weekly_response.context["top_sellers"][0]["total"], decimal.Decimal("325.00"))

    def test_tab_parameter_selects_tab_and_is_preserved_by_filters(self):
        response = self.get_leaderboard(2, tab="dens")

        self.assertEqual(response.context["selected_leaderboard_tab"], "dens")
        self.assertContains(response, 'class="nav-link active"')
        self.assertContains(response, 'class="tab-pane fade show active"')
        self.assertContains(response, 'name="tab" value="dens"', count=1)

    def test_invalid_tab_falls_back_to_top_sales(self):
        response = self.get_leaderboard(tab="unknown")

        self.assertEqual(response.context["selected_leaderboard_tab"], "top-sales")
        self.assertContains(response, 'name="tab" value="top-sales"', count=1)

    def test_unknown_campaign_returns_not_found(self):
        response = self.client.get(
            reverse(
                "campaigns:order_leaderboard_by_campaign",
                args=[self.pack_year.year - 10],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_campaign_returns_not_found(self):
        response = self.client.get("/ncc/leaderboard/invalid/")

        self.assertEqual(response.status_code, 404)

    def test_leaderboard_index_renders_latest_campaign_and_honors_query_state(self):
        response = self.client.get(reverse("campaigns:order_leaderboard"), {"tab": "dens", "week": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["campaigns"]["viewing"], self.campaign)
        self.assertEqual(response.context["selected_leaderboard_tab"], "dens")
        self.assertEqual(response.context["selected_leaderboard_week"]["number"], 2)
