from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.campaigns.models import Campaign, Customer, Order, Quota
from packman.campaigns.templatetags.campaign_extras import quota_progress
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory


def _start_of_day(a_date):
    """Convert a date into an aware datetime at midnight, for use with Campaign's
    DateTimeField ordering_opens/ordering_closes."""
    return timezone.make_aware(timezone.datetime.combine(a_date, timezone.datetime.min.time()))


class QuotaProgressTagTest(TestCase):
    def setUp(self):
        self.pack_year = CurrentPackYearFactory()
        self.family = FamilyFactory()
        self.adult = AdultFactory(family=self.family, is_active=True)
        self.scout = ActiveScoutFactory(family=self.family)
        self.campaign = Campaign.objects.create(
            year=self.pack_year,
            ordering_opens=_start_of_day(self.pack_year.start_date),
            ordering_closes=_start_of_day(self.pack_year.end_date),
            delivery_available=self.pack_year.end_date,
            prize_window_opens=self.pack_year.start_date,
            prize_window_closes=self.pack_year.end_date,
        )
        self.customer = Customer.objects.create(name="Test Customer", address="123 Main St")

    def _add_order(self, donation):
        return Order.objects.create(
            seller=self.scout,
            customer=self.customer,
            campaign=self.campaign,
            recorded_by=self.adult,
            donation=donation,
        )

    def _set_quota(self, target):
        membership = self.scout.den_memberships.get(year_assigned=self.pack_year)
        Quota.objects.create(campaign=self.campaign, den=membership.den, target=target)

    def _current_total(self):
        products_total = self.scout.orders.current_campaign().products_total()["total"]
        donations_total = self.scout.orders.current_campaign().donations_total()["total"]
        return products_total + donations_total

    @staticmethod
    def _total_pct(progress):
        return sum(segment["pct"] for segment in progress["segments"])

    @staticmethod
    def _earned_pct(progress):
        """Sum of segments representing actually-earned progress (excludes
        the translucent "remaining" segment, which is tagged with an
        `opacity`)."""
        return sum(segment["pct"] for segment in progress["segments"] if "opacity" not in segment)

    def test_no_orders_reports_zero_progress(self):
        self._set_quota(Decimal("550"))
        progress = quota_progress(self.scout, self.campaign)
        self.assertEqual(progress["next_tier_label"], "Quota: $550.00")
        self.assertEqual(progress["total"], Decimal("0.00"))
        self.assertEqual(self._earned_pct(progress), 0)
        # The whole bar should still be colored (the quota tier's color, at
        # reduced opacity) rather than left blank.
        self.assertAlmostEqual(self._total_pct(progress), 100, places=1)

    def test_segments_are_continuous_across_bronze_boundary(self):
        self._set_quota(Decimal("550"))
        self._add_order(Decimal("550"))  # exactly at quota — quota is now considered met

        at_quota = quota_progress(self.scout, self.campaign)
        self.assertEqual(at_quota["next_tier_label"], "Bronze Medal: $1,000")
        at_quota_earned = self._earned_pct(at_quota)

        self._add_order(Decimal("1"))  # just over quota, into bronze tier
        just_over = quota_progress(self.scout, self.campaign)
        self.assertEqual(just_over["next_tier_label"], "Bronze Medal: $1,000")
        # Earned progress should barely move right after crossing quota,
        # not jump ahead.
        just_over_earned = self._earned_pct(just_over)
        self.assertLess(just_over_earned - at_quota_earned, 1)

    def test_totals_sum_to_full_bar_at_each_milestone(self):
        self._set_quota(Decimal("550"))
        # The bar's 100% mark is the ceiling of whichever tier the total
        # currently lands in, not always $2,000, so earned progress should
        # always equal total / that tier's ceiling.
        tier_ceiling = {
            "Bronze Medal: $1,000": Decimal("1000"),
            "Silver Medal: $1,500": Decimal("1500"),
            "Gold Medal: $2,000": Decimal("2000"),
            # Exactly meeting the last milestone reads as "beyond" it, same
            # as any other tier boundary.
            "Golden Peanut Contender": Decimal("2000"),
        }
        for milestone in (Decimal("1000"), Decimal("1500"), Decimal("2000")):
            self._add_order(milestone - self._current_total())
            progress = quota_progress(self.scout, self.campaign)
            ceiling = tier_ceiling[progress["next_tier_label"]]
            self.assertAlmostEqual(self._earned_pct(progress), float(milestone) / float(ceiling) * 100, places=1)
            # Filled + remaining should always add up to a full bar.
            self.assertAlmostEqual(self._total_pct(progress), 100, places=1)

    def test_beyond_gold_fills_entire_bar_with_no_remaining_segment(self):
        self._set_quota(Decimal("550"))
        self._add_order(Decimal("2500"))
        progress = quota_progress(self.scout, self.campaign)
        self.assertEqual(progress["next_tier_label"], "Golden Peanut Contender")
        self.assertAlmostEqual(self._earned_pct(progress), 100, places=1)
        self.assertTrue(all("opacity" not in segment for segment in progress["segments"]))

    def test_bar_ends_at_top_of_current_tier_not_gold(self):
        self._set_quota(Decimal("550"))
        self._add_order(Decimal("900"))  # in bronze tier, well under $2,000
        progress = quota_progress(self.scout, self.campaign)
        self.assertEqual(progress["next_tier_label"], "Bronze Medal: $1,000")
        # The bar should read as ~90% earned (900 of the bronze tier's
        # $1,000 ceiling), not ~45% (900 of a $2,000 baseline).
        self.assertAlmostEqual(self._earned_pct(progress), 90, places=1)

    def test_segment_colors_match_expected_tiers(self):
        self._set_quota(Decimal("550"))
        self._add_order(Decimal("900"))  # in bronze tier
        progress = quota_progress(self.scout, self.campaign)
        colors = [segment["color"] for segment in progress["segments"]]
        self.assertIn("var(--bs-primary)", colors)  # quota segment
        self.assertIn("#977547", colors)  # bronze segment(s), earned + remaining

    def test_progress_text_reflects_milestone_just_reached(self):
        self._set_quota(Decimal("550"))
        self.assertEqual(quota_progress(self.scout, self.campaign)["progress_text"], "Working on making Quota!")

        self._add_order(Decimal("550"))
        self.assertEqual(quota_progress(self.scout, self.campaign)["progress_text"], "Quota Met!")

        self._add_order(Decimal("450"))  # total 1000, into silver tier
        self.assertEqual(quota_progress(self.scout, self.campaign)["progress_text"], "Bronze Medal Earned!")

        self._add_order(Decimal("500"))  # total 1500, into gold tier
        self.assertEqual(quota_progress(self.scout, self.campaign)["progress_text"], "Silver Medal Earned!")

        self._add_order(Decimal("501"))  # total 2001, beyond gold
        self.assertEqual(quota_progress(self.scout, self.campaign)["progress_text"], "Gold Medal Earned!")

    def test_raises_if_scout_has_no_quota_configured(self):
        with self.assertRaises(Quota.DoesNotExist):
            quota_progress(self.scout, self.campaign)
