import decimal

from django.contrib import admin
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.campaigns.admin import OrderAdmin, OrderAdminForm
from packman.campaigns.forms import OrderForm
from packman.campaigns.models import Campaign, Category, Customer, Order, OrderItem, PrizePoint, Product, Quota
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory


class AwardEligibilityTestCase(TestCase):
    def setUp(self):
        self.pack_year = CurrentPackYearFactory()
        self.family = FamilyFactory()
        self.adult = AdultFactory(family=self.family, is_active=True)
        self.scout = ActiveScoutFactory(family=self.family)
        now = timezone.now()
        self.campaign = Campaign.objects.create(
            year=self.pack_year,
            ordering_opens=now - timezone.timedelta(days=1),
            ordering_closes=now + timezone.timedelta(days=10),
            delivery_available=(now + timezone.timedelta(days=15)).date(),
            prize_window_opens=(now - timezone.timedelta(days=1)).date(),
            prize_window_closes=(now + timezone.timedelta(days=30)).date(),
        )
        membership = self.scout.den_memberships.get(year_assigned=self.pack_year)
        self.den = membership.den
        Quota.objects.create(campaign=self.campaign, den=self.den, target=decimal.Decimal("550.00"))
        self.customer = Customer.objects.create(name="Eligible Customer")
        self.client.force_login(self.adult)

    def create_order(self, donation, award_ineligible=None, customer=None):
        return Order.objects.create(
            campaign=self.campaign,
            seller=self.scout,
            customer=customer or self.customer,
            recorded_by=self.adult,
            donation=decimal.Decimal(donation),
            award_ineligible=award_ineligible,
        )

    def test_award_eligible_scope_includes_null_and_false(self):
        default_order = self.create_order("100.00")
        false_order = self.create_order("200.00", award_ineligible=False)
        excluded_order = self.create_order("300.00", award_ineligible=True)

        self.assertIsNone(default_order.award_ineligible)
        self.assertQuerySetEqual(
            Order.objects.award_eligible().order_by("donation"),
            [default_order, false_order],
        )
        self.assertNotIn(excluded_order, Order.objects.award_eligible())

    def test_flag_is_available_only_in_admin(self):
        model_admin = admin.site._registry[Order]

        self.assertIsInstance(model_admin, OrderAdmin)
        self.assertIn("is_award_ineligible", model_admin.list_display)
        self.assertIn("award_ineligible", model_admin.list_filter)
        self.assertNotIn("award_ineligible", OrderForm.base_fields)

    def test_admin_shows_null_as_no_and_does_not_persist_false(self):
        order = self.create_order("100.00", award_ineligible=True)
        model_admin = admin.site._registry[Order]
        form = OrderAdminForm(
            data={
                "campaign": self.campaign.pk,
                "seller": self.scout.pk,
                "customer": self.customer.pk,
                "recorded_by": self.adult.pk,
                "donation": "100.00",
                "notes": "",
                "latitude": "",
                "longitude": "",
                "gps_accuracy": "",
                "date_paid": "",
                "date_delivered": "",
            },
            instance=order,
        )

        self.assertEqual(form.fields["award_ineligible"].label, "Award Ineligible")
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        order.refresh_from_db()
        self.assertIsNone(order.award_ineligible)
        self.assertFalse(model_admin.is_award_ineligible(order))

    def test_leaderboard_excludes_ineligible_order_totals_and_counts(self):
        self.create_order("600.00")
        self.create_order("1000.00", award_ineligible=True)

        response = self.client.get(reverse("campaigns:order_leaderboard_by_campaign", args=[self.pack_year.year]))

        cub = response.context["top_sellers"][0]
        self.assertEqual(cub["orders"], 1)
        self.assertEqual(cub["total"], decimal.Decimal("600.00"))
        self.assertEqual(response.context["dens"][0]["orders"], 1)
        self.assertEqual(response.context["dens"][0]["total"], decimal.Decimal("600.00"))

    def test_prize_selection_excludes_ineligible_orders(self):
        PrizePoint.objects.create(earned_at=decimal.Decimal("550.00"), value=5)
        PrizePoint.objects.create(earned_at=decimal.Decimal("1000.00"), value=10)
        self.create_order("600.00")
        self.create_order("1000.00", award_ineligible=True)

        response = self.client.get(reverse("campaigns:prize_selection"))

        self.assertEqual(response.context["total"], decimal.Decimal("600.00"))
        self.assertEqual(response.context["cub_list"][0]["points"]["earned"], 5)

    def test_prize_selection_uses_configured_tier_steps_above_highest_tier(self):
        PrizePoint.objects.create(earned_at=decimal.Decimal("1000.00"), value=10)
        PrizePoint.objects.create(earned_at=decimal.Decimal("2000.00"), value=25)
        self.create_order("4000.00")

        response = self.client.get(reverse("campaigns:prize_selection"))

        self.assertEqual(response.context["cub_list"][0]["points"]["earned"], 55)

    def test_order_report_includes_ineligible_orders(self):
        self.create_order("100.00")
        self.create_order("1000.00", award_ineligible=True)

        response = self.client.get(reverse("campaigns:order_report"))

        self.assertEqual(response.context["report"]["count"], 2)
        self.assertEqual(response.context["report"]["total"], decimal.Decimal("1100.00"))
        day = list(response.context["report"]["days"])[0]
        self.assertEqual(day["count"], 2)
        self.assertEqual(day["order_total"], decimal.Decimal("1100.00"))

    def test_order_slip_seller_summary_excludes_ineligible_orders(self):
        category = Category.objects.create(name="Snacks")
        product = Product.objects.create(
            name="Popcorn",
            category=category,
            campaign=self.campaign,
            price=decimal.Decimal("1.00"),
        )
        eligible_order = self.create_order("1200.00")
        ineligible_customer = Customer.objects.create(name="Ineligible Customer")
        ineligible_order = self.create_order(
            "1000.00",
            award_ineligible=True,
            customer=ineligible_customer,
        )
        OrderItem.objects.create(order=eligible_order, product=product)
        OrderItem.objects.create(order=ineligible_order, product=product)

        content = render_to_string(
            "campaigns/reports/order_slips.html",
            {"order_list": [eligible_order, ineligible_order]},
        )

        self.assertIn("1 order", content)
        self.assertIn("$1,201 Total Sales", content)
        self.assertIn("Bronze Medal Winner!", content)
        self.assertNotIn("Silver Medal Winner!", content)
        self.assertIn("Eligible Customer", content)
        self.assertIn("Ineligible Customer", content)
