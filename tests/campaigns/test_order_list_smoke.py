import re

from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.campaigns.models import Campaign, Customer, Order, Quota
from packman.dens.models import Membership
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory


def _start_of_day(a_date):
    """Convert a date into an aware datetime at midnight, for use with Campaign's
    DateTimeField ordering_opens/ordering_closes."""
    return timezone.make_aware(timezone.datetime.combine(a_date, timezone.datetime.min.time()))


class OrderListSmokeTest(TestCase):
    def setUp(self):
        self.pack_year = CurrentPackYearFactory()
        self.family = FamilyFactory()
        self.adult = AdultFactory(family=self.family, is_active=True)
        self.scout1 = ActiveScoutFactory(family=self.family)
        self.scout2 = ActiveScoutFactory(family=self.family)
        self.campaign = Campaign.objects.create(
            year=self.pack_year,
            ordering_opens=_start_of_day(self.pack_year.start_date),
            ordering_closes=_start_of_day(self.pack_year.end_date),
            delivery_available=self.pack_year.end_date,
            prize_window_opens=self.pack_year.start_date,
            prize_window_closes=self.pack_year.end_date,
        )
        self.customer = Customer.objects.create(name="Test Customer", address="123 Main St")
        self._set_quota(self.scout1, 550)
        self._set_quota(self.scout2, 550)
        Order.objects.create(
            seller=self.scout1, customer=self.customer, campaign=self.campaign, recorded_by=self.adult
        )
        Order.objects.create(
            seller=self.scout2, customer=self.customer, campaign=self.campaign, recorded_by=self.adult
        )

    def _set_quota(self, scout, target):
        membership = scout.den_memberships.get(year_assigned=self.pack_year)
        Quota.objects.create(campaign=self.campaign, den=membership.den, target=target)

    def test_order_list_renders(self):
        self.client.force_login(self.adult)
        resp = self.client.get("/ncc/")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Cubs", content)
        self.assertEqual(len(re.findall(r"<h1>\s*Orders\s*</h1>", content)), 1)

    def test_order_list_filtered_by_seller(self):
        self.client.force_login(self.adult)
        resp = self.client.get(f"/ncc/?seller={self.scout1.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context["order_list"]), [Order.objects.get(seller=self.scout1)])

    def test_award_ineligible_label_only_appears_for_all_cubs(self):
        order = Order.objects.get(seller=self.scout1)
        order.award_ineligible = True
        order.save()
        self.client.force_login(self.adult)

        all_cubs_response = self.client.get("/ncc/")
        selected_cub_response = self.client.get(f"/ncc/?seller={self.scout1.pk}")

        self.assertContains(all_cubs_response, "Award Ineligible")
        self.assertNotContains(all_cubs_response, "badge text-bg-info")
        self.assertNotContains(selected_cub_response, "Award Ineligible")
        self.assertEqual(list(selected_cub_response.context["order_list"]), [])

    def test_cub_with_no_orders_still_shown(self):
        scout_no_orders = ActiveScoutFactory(family=self.family)
        self._set_quota(scout_no_orders, 550)
        self.client.force_login(self.adult)
        resp = self.client.get("/ncc/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(scout_no_orders, resp.context["sellers"])

    def test_cub_with_no_orders_shows_zero_totals(self):
        scout_no_orders = ActiveScoutFactory(family=self.family)
        self._set_quota(scout_no_orders, 550)
        self.client.force_login(self.adult)
        resp = self.client.get("/ncc/")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        heading_index = content.index(scout_no_orders.short_name)
        following_content = content[heading_index : heading_index + 2000]
        self.assertIn("$ 0", following_content)
        self.assertNotIn("$ None", following_content)

    def test_past_campaign_only_shows_scouts_with_orders(self):
        past_year = PackYearFactory(year=self.pack_year.year - 5)
        past_campaign = Campaign.objects.create(
            year=past_year,
            ordering_opens=_start_of_day(past_year.start_date),
            ordering_closes=_start_of_day(past_year.end_date),
            delivery_available=past_year.end_date,
            prize_window_opens=past_year.start_date,
            prize_window_closes=past_year.end_date,
        )
        # scout1 sold in the past campaign and has a den/quota for it;
        # scout2 was around but didn't sell, so shouldn't show up.
        past_den = self.scout1.den_memberships.get(year_assigned=self.pack_year).den
        Membership.objects.create(scout=self.scout1, den=past_den, year_assigned=past_year)
        Quota.objects.create(campaign=past_campaign, den=past_den, target=550)
        Order.objects.create(
            seller=self.scout1, customer=self.customer, campaign=past_campaign, recorded_by=self.adult
        )

        self.client.force_login(self.adult)
        resp = self.client.get(f"/ncc/{past_year.year}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.scout1, resp.context["sellers"])
        self.assertNotIn(self.scout2, resp.context["sellers"])
