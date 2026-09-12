import decimal
from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import PackYearFactory
from packman.campaigns.models import (
    Campaign,
    Category,
    Customer,
    Order,
    OrderItem,
    Prize,
    PrizePoint,
    PrizeSelection,
    Product,
    Quota,
)
from packman.campaigns.report_data import build_cub_report
from packman.dens.factories import DenFactory, MembershipFactory
from packman.membership.factories import AdultFactory, CompleteFamilyFactory, ScoutFactory


class CampaignReportTestCase(TestCase):
    def setUp(self):
        self.current_year = PackYearFactory(year=2026)
        self.previous_year = PackYearFactory(year=2025)
        # Anchor the campaign windows to "today" (well outside Campaign.objects.current()'s
        # 90-day lookback) rather than hardcoded calendar dates, so these tests don't become
        # flaky/incorrect depending on what day they happen to run.
        today = timezone.now()
        self.previous_campaign = self.create_campaign(self.previous_year, today - timezone.timedelta(days=400))
        self.current_campaign = self.create_campaign(self.current_year, today - timezone.timedelta(days=200))

    def create_campaign(self, year, ordering_opens):
        return Campaign.objects.create(
            year=year,
            ordering_opens=ordering_opens,
            ordering_closes=ordering_opens + timezone.timedelta(days=30),
            delivery_available=ordering_opens + timezone.timedelta(days=45),
            prize_window_opens=ordering_opens + timezone.timedelta(days=45),
            prize_window_closes=ordering_opens + timezone.timedelta(days=60),
        )

    def test_cub_report_only_includes_selected_campaign_orders_and_members(self):
        current_member = MembershipFactory(year_assigned=self.current_year)
        previous_member = MembershipFactory(year_assigned=self.previous_year)
        Order.objects.create(
            campaign=self.current_campaign, seller=current_member.scout, donation=decimal.Decimal("25.00")
        )
        Order.objects.create(
            campaign=self.previous_campaign, seller=previous_member.scout, donation=decimal.Decimal("50.00")
        )

        report = build_cub_report(
            self.current_campaign,
            Order.objects.filter(campaign=self.current_campaign),
            include_campaign_fields=False,
        )
        row = report.rows[0]

        self.assertEqual(
            [str(column.label) for column in report.columns],
            ["Cub", "Den", "Order Count", "Total Sales", "Eligible Total"],
        )
        self.assertEqual(len(report.rows), 1)
        self.assertEqual(row[0].value, current_member.scout)
        self.assertEqual(row[1].value, current_member.den)
        self.assertEqual([cell.value for cell in row[2:]], [1, decimal.Decimal("25"), decimal.Decimal("25")])

    def test_cub_report_uses_the_den_assigned_for_the_campaign_year(self):
        # A scout who moved dens between pack years must be reported under the
        # den they belonged to during the campaign's year, not their den from
        # any other year (and not necessarily their "current" den).
        scout = ScoutFactory()
        old_den = DenFactory()
        new_den = DenFactory()
        MembershipFactory(scout=scout, den=old_den, year_assigned=self.previous_year)
        MembershipFactory(scout=scout, den=new_den, year_assigned=self.current_year)
        Order.objects.create(campaign=self.current_campaign, seller=scout, donation=decimal.Decimal("10.00"))

        report = build_cub_report(
            self.current_campaign,
            Order.objects.filter(campaign=self.current_campaign),
            include_campaign_fields=False,
        )

        self.assertEqual(len(report.rows), 1)
        self.assertEqual(report.rows[0][0].value, scout)
        self.assertEqual(report.rows[0][1].value, new_den)

    def test_campaign_report_uses_campaign_quota_and_tiered_prize_points(self):
        member = MembershipFactory(year_assigned=self.current_year)
        Quota.objects.create(campaign=self.current_campaign, den=member.den, target=decimal.Decimal("100.00"))
        Quota.objects.create(campaign=self.previous_campaign, den=member.den, target=decimal.Decimal("4000.00"))
        PrizePoint.objects.create(earned_at=decimal.Decimal("1000.00"), value=10)
        PrizePoint.objects.create(earned_at=decimal.Decimal("2000.00"), value=25)
        Order.objects.create(campaign=self.current_campaign, seller=member.scout, donation=decimal.Decimal("4000.00"))

        report = build_cub_report(
            self.current_campaign,
            Order.objects.filter(campaign=self.current_campaign),
            include_campaign_fields=True,
        )
        row = report.rows[0]

        self.assertEqual(row[5].value, decimal.Decimal("100.00"))
        self.assertEqual(row[8].value, 55)

    def test_campaign_report_splits_operational_and_award_totals(self):
        member = MembershipFactory(year_assigned=self.current_year)
        Quota.objects.create(campaign=self.current_campaign, den=member.den, target=decimal.Decimal("500.00"))
        PrizePoint.objects.create(earned_at=decimal.Decimal("500.00"), value=5)
        PrizePoint.objects.create(earned_at=decimal.Decimal("1000.00"), value=10)
        Order.objects.create(campaign=self.current_campaign, seller=member.scout, donation=decimal.Decimal("100.00"))
        Order.objects.create(
            campaign=self.current_campaign,
            seller=member.scout,
            donation=decimal.Decimal("1000.00"),
            award_ineligible=True,
        )

        report = build_cub_report(
            self.current_campaign,
            Order.objects.filter(campaign=self.current_campaign),
            include_campaign_fields=True,
        )
        row = report.rows[0]

        self.assertEqual(
            [str(column.label) for column in report.columns[3:6]], ["Total Sales", "Eligible Total", "Quota"]
        )
        self.assertEqual(row[2].value, 2)
        self.assertEqual(row[3].value, decimal.Decimal("1100.00"))
        self.assertEqual(row[4].value, decimal.Decimal("100.00"))
        self.assertFalse(row[6].value)
        self.assertEqual(row[7].value, decimal.Decimal("1100.00"))
        self.assertEqual(row[8].value, 0)

    def test_cub_report_includes_ineligible_orders_in_operational_totals(self):
        member = MembershipFactory(year_assigned=self.current_year)
        Order.objects.create(
            campaign=self.current_campaign,
            seller=member.scout,
            donation=decimal.Decimal("25.00"),
            award_ineligible=True,
        )

        report = build_cub_report(
            self.current_campaign,
            Order.objects.filter(campaign=self.current_campaign),
            include_campaign_fields=False,
        )

        self.assertEqual([cell.value for cell in report.rows[0][2:]], [1, decimal.Decimal("25"), decimal.Decimal("0")])


class OrderReportViewTestCase(TestCase):
    def setUp(self):
        self.current_year = PackYearFactory(year=2026)
        self.previous_year = PackYearFactory(year=2025)
        self.campaign_start = timezone.now().replace(minute=0, second=0, microsecond=0) - timezone.timedelta(days=20)
        self.current_campaign = self.create_campaign(self.current_year, self.campaign_start)
        self.previous_campaign = self.create_campaign(
            self.previous_year,
            self.campaign_start - timezone.timedelta(days=365),
        )
        self.user = AdultFactory()
        permission = Permission.objects.get(
            codename="generate_order_report",
            content_type=ContentType.objects.get_for_model(Campaign),
        )
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        self.member = MembershipFactory(year_assigned=self.current_year)
        self.customer = Customer.objects.create(name="Report Customer")
        self.category = Category.objects.create(name="Popcorn")
        self.product = Product.objects.create(
            name="Caramel Corn",
            category=self.category,
            campaign=self.current_campaign,
            price=decimal.Decimal("10.00"),
        )

    def create_campaign(self, year, ordering_opens):
        return Campaign.objects.create(
            year=year,
            ordering_opens=ordering_opens,
            ordering_closes=ordering_opens + timezone.timedelta(days=21),
            delivery_available=(ordering_opens + timezone.timedelta(days=30)).date(),
            prize_window_opens=ordering_opens.date(),
            prize_window_closes=(ordering_opens + timezone.timedelta(days=35)).date(),
        )

    def create_order(self, day, quantity):
        order = Order.objects.create(
            campaign=self.current_campaign,
            seller=self.member.scout,
            customer=self.customer,
            recorded_by=self.user,
        )
        Order.objects.filter(pk=order.pk).update(date_added=self.campaign_start + timezone.timedelta(days=day))
        OrderItem.objects.create(order=order, product=self.product, quantity=quantity)
        return order

    def test_report_renders_five_tabs_and_cubs_table(self):
        response = self.client.get(reverse("campaigns:order_report"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NCC Dashboard")
        self.assertEqual(response.context["selected_tab"], "sales")
        self.assertContains(response, "data-campaign-tab=", count=5)
        self.assertContains(response, 'aria-current="page"', count=1)
        self.assertNotContains(response, 'data-bs-toggle="tab"')
        self.assertContains(response, "Sales")
        self.assertContains(response, "Products")
        self.assertContains(response, "Cubs")
        self.assertContains(response, "Prize Selections")
        self.assertContains(response, "Pack Night")
        self.assertNotContains(response, "data-sortable-report-table")
        self.assertNotContains(response, "js/report_tables.js")
        self.assertIn("sales", response.context)
        self.assertNotIn("product_report", response.context)
        self.assertNotIn("cub_report", response.context)

        cubs_response = self.client.get(reverse("campaigns:order_report"), {"tab": "cubs"})
        self.assertEqual(cubs_response.context["selected_tab"], "cubs")
        self.assertContains(cubs_response, 'id="cubs_report_table"')
        self.assertContains(cubs_response, 'data-csv-table-id="cubs_report_table"')
        self.assertContains(cubs_response, f'data-csv-filename="{self.current_year.year}-cubs-full-campaign.csv"')
        self.assertContains(cubs_response, "Download CSV", count=1)
        self.assertContains(cubs_response, "data-sortable-report-table", count=1)
        self.assertContains(cubs_response, 'aria-sort="descending"', count=1)
        self.assertNotIn("sales", cubs_response.context)
        self.assertNotIn("product_report", cubs_response.context)

        packing_response = self.client.get(reverse("campaigns:order_report"), {"tab": "packing-night"})
        for url_name in ("place_markers", "pull_sheets", "order_slips"):
            self.assertContains(packing_response, reverse(f"campaigns:{url_name}"))
        self.assertNotIn("sales", packing_response.context)
        self.assertNotIn("product_report", packing_response.context)
        self.assertNotIn("cub_report", packing_response.context)

    def test_all_campaign_weeks_are_available_without_visibility_rules(self):
        response = self.client.get(reverse("campaigns:order_report"), {"week": 3})

        self.assertEqual([week["number"] for week in response.context["weeks"]], [1, 2, 3])
        self.assertEqual(response.context["selected_week"]["number"], 3)
        self.assertContains(response, "Week 3")

    def test_week_filter_uses_opening_time_and_filters_sales_and_products(self):
        self.create_order(day=6, quantity=2)
        self.create_order(day=7, quantity=5)

        first_week = self.client.get(reverse("campaigns:order_report"), {"week": 1})
        second_week = self.client.get(reverse("campaigns:order_report"), {"week": 2})
        first_week_products = self.client.get(
            reverse("campaigns:order_report"),
            {"tab": "products", "week": 1},
        )
        second_week_products = self.client.get(
            reverse("campaigns:order_report"),
            {"tab": "products", "week": 2},
        )

        self.assertEqual(first_week.context["sales"]["count"], 1)
        self.assertEqual(first_week.context["sales"]["total"], decimal.Decimal("20.00"))
        self.assertEqual(second_week.context["sales"]["count"], 1)
        self.assertEqual(second_week.context["sales"]["total"], decimal.Decimal("50.00"))
        self.assertEqual(first_week_products.context["product_report"].rows[0][1].value, 2)
        self.assertEqual(second_week_products.context["product_report"].rows[0][1].value, 5)
        self.assertNotIn("sales", first_week_products.context)
        self.assertNotIn("sales", second_week_products.context)

    def test_cubs_report_uses_weekly_core_columns_and_campaign_final_columns(self):
        self.create_order(day=6, quantity=2)
        self.create_order(day=7, quantity=5)

        weekly_response = self.client.get(
            reverse("campaigns:order_report"),
            {"tab": "cubs", "week": 1},
        )
        campaign_response = self.client.get(reverse("campaigns:order_report"), {"tab": "cubs"})

        weekly_report = weekly_response.context["cub_report"]
        campaign_report = campaign_response.context["cub_report"]
        self.assertEqual(
            [str(column.label) for column in weekly_report.columns],
            ["Cub", "Den", "Order Count", "Total Sales", "Eligible Total"],
        )
        self.assertEqual(weekly_report.rows[0][2].value, 1)
        self.assertEqual(weekly_report.rows[0][3].value, decimal.Decimal("20.00"))
        self.assertEqual(weekly_report.rows[0][1].effective_sort_value, self.member.den.number)
        self.assertEqual(weekly_report.default_sort_index, 4)
        self.assertEqual(weekly_report.default_sort_direction, "descending")
        self.assertEqual(len(campaign_report.columns), 11)
        self.assertEqual(campaign_report.default_sort_index, 4)
        self.assertEqual(campaign_report.default_sort_direction, "descending")
        self.assertEqual(campaign_report.rows[0][2].value, 2)
        self.assertEqual(campaign_report.rows[0][3].value, decimal.Decimal("70.00"))
        self.assertContains(weekly_response, "Cubs — Week 1")
        self.assertContains(campaign_response, "Cubs — Full Campaign")

    def test_cubs_report_uses_compact_currency_formatting(self):
        Quota.objects.create(
            campaign=self.current_campaign,
            den=self.member.den,
            target=decimal.Decimal("100.00"),
        )
        Order.objects.create(
            campaign=self.current_campaign,
            seller=self.member.scout,
            donation=decimal.Decimal("25.50"),
        )

        response = self.client.get(reverse("campaigns:order_report"), {"tab": "cubs"})

        self.assertContains(response, "$25.50", count=2)
        self.assertContains(response, "$100", count=1)
        self.assertNotContains(response, "$100.00")

    def test_cubs_and_products_download_buttons_target_visible_tables(self):
        self.create_order(day=6, quantity=2)

        for tab, table_id in (
            ("cubs", "cubs_report_table"),
            ("products", "products_ordered_table"),
        ):
            with self.subTest(tab=tab):
                page_response = self.client.get(
                    reverse("campaigns:order_report"),
                    {"tab": tab, "week": 1},
                )

                self.assertContains(page_response, f'id="{table_id}"')
                self.assertContains(page_response, f'data-csv-table-id="{table_id}"')
                self.assertContains(
                    page_response,
                    f'data-csv-filename="{self.current_year.year}-{tab}-week-1.csv"',
                )
                if tab == "products":
                    report = page_response.context["product_report"]
                    self.assertEqual(report.default_sort_index, 1)
                    self.assertEqual(report.default_sort_direction, "descending")

    def test_sales_report_includes_dates_without_orders(self):
        self.create_order(day=2, quantity=3)

        response = self.client.get(reverse("campaigns:order_report"), {"week": 1})

        days = response.context["sales"]["days"]
        self.assertEqual(days[0]["date"], timezone.localtime(self.campaign_start).date())
        self.assertEqual(
            days[-1]["date"],
            timezone.localtime(self.campaign_start + timezone.timedelta(days=7)).date(),
        )
        self.assertEqual(len(days), 8)
        self.assertEqual(days[0]["count"], 0)
        self.assertEqual(days[0]["order_total"], decimal.Decimal("0.00"))
        self.assertEqual(days[2]["count"], 1)
        self.assertEqual(days[2]["order_total"], decimal.Decimal("30.00"))
        self.assertEqual(days[-1]["count"], 0)

    def test_campaign_selection_filters_prizes_and_uses_historical_den(self):
        historical_member = MembershipFactory(
            scout=self.member.scout,
            year_assigned=self.previous_year,
        )
        prize = Prize.objects.create(
            name="Past Campaign Compass",
            points=5,
            campaign=self.previous_campaign,
        )
        PrizeSelection.objects.create(
            campaign=self.previous_campaign,
            cub=self.member.scout,
            prize=prize,
            quantity=2,
        )

        response = self.client.get(
            reverse("campaigns:order_report_by_campaign", args=[self.previous_year.year]),
            {"tab": "prize-selections"},
        )

        self.assertEqual(response.context["campaigns"]["viewing"], self.previous_campaign)
        self.assertEqual(response.context["selected_tab"], "prize-selections")
        self.assertEqual(response.context["prize_totals_report"].rows[0][1].value, 2)
        self.assertEqual(response.context["prize_selections_report"].rows[0][0].value, historical_member.den.number)
        self.assertEqual(response.context["prize_totals_report"].default_sort_index, 1)
        self.assertEqual(response.context["prize_totals_report"].default_sort_direction, "descending")
        self.assertEqual(response.context["prize_selections_report"].default_sort_index, 1)
        self.assertEqual(response.context["prize_selections_report"].default_sort_direction, "ascending")
        self.assertContains(response, "Past Campaign Compass")
        self.assertContains(response, str(historical_member.den.number))
        self.assertContains(response, "Download CSV", count=2)
        self.assertContains(response, "data-sortable-report-table", count=2)
        self.assertContains(response, 'aria-sort="descending"', count=1)
        self.assertContains(response, 'aria-sort="ascending"', count=1)
        self.assertContains(response, 'data-csv-table-id="prize_totals_table"')
        self.assertContains(response, 'data-csv-table-id="prize_selections_table"')
        self.assertContains(
            response,
            f'data-csv-filename="{self.previous_year.year}-prize-totals.csv"',
        )
        self.assertContains(
            response,
            f'data-csv-filename="{self.previous_year.year}-prize-selections-by-cub.csv"',
        )

    def test_cub_report_uses_a_bounded_number_of_queries(self):
        PrizePoint.objects.create(earned_at=decimal.Decimal("10.00"), value=1)
        PrizePoint.objects.create(earned_at=decimal.Decimal("20.00"), value=2)
        for _ in range(3):
            MembershipFactory(year_assigned=self.current_year)

        orders = Order.objects.filter(campaign=self.current_campaign)
        with CaptureQueriesContext(connection) as queries:
            report = build_cub_report(self.current_campaign, orders, include_campaign_fields=True)

        self.assertEqual(len(report.rows), 4)
        self.assertLessEqual(len(queries), 5)

    def test_invalid_state_is_handled_consistently(self):
        response = self.client.get(reverse("campaigns:order_report"), {"tab": "unknown"})
        self.assertEqual(response.context["selected_tab"], "sales")

        for week in ("unknown", 4):
            with self.subTest(week=week):
                response = self.client.get(reverse("campaigns:order_report"), {"week": week})
                self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse("campaigns:order_report_by_campaign", args=[1900]),
        )
        self.assertEqual(response.status_code, 404)

    def test_standalone_prize_selection_report_route_is_removed(self):
        response = self.client.get(f"{reverse('campaigns:order_report')}prize_selections/")

        self.assertEqual(response.status_code, 404)


class CampaignReportAccessControlTestCase(TestCase):

    def setUp(self):
        current_year = PackYearFactory(year=2026)
        Campaign.objects.create(
            year=current_year,
            ordering_opens=timezone.make_aware(timezone.datetime(2026, 9, 1)),
            ordering_closes=timezone.make_aware(timezone.datetime(2026, 10, 1)),
            delivery_available=timezone.datetime(2026, 10, 15).date(),
            prize_window_opens=timezone.datetime(2026, 10, 15).date(),
            prize_window_closes=timezone.datetime(2026, 10, 30).date(),
        )

        content_type = ContentType.objects.get_for_model(Campaign)
        self.permission = Permission.objects.get(codename="generate_order_report", content_type=content_type)

    def test_order_report_redirects_anonymous_user_to_login(self):
        url = reverse("campaigns:order_report")
        login_url = f"{reverse('login')}?next={url}"
        response = self.client.get(url)

        self.assertRedirects(response, login_url)

    def test_order_report_denies_member_without_permission(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(reverse("campaigns:order_report"))

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_order_report_allows_member_with_permission(self):
        member = AdultFactory()
        member.user_permissions.add(self.permission)
        self.client.force_login(member)
        response = self.client.get(reverse("campaigns:order_report"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
