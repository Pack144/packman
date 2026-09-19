import decimal
import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import CurrentPackYearFactory
from packman.campaigns.models import Campaign, Prize, PrizeSelection, Quota
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory


class PrizeSelectionWindowTests(TestCase):
    def setUp(self):
        family = FamilyFactory()
        self.adult = AdultFactory(family=family, is_active=True)
        self.scout = ActiveScoutFactory(family=family)
        now = timezone.now()
        today = timezone.localdate()
        self.campaign = Campaign.objects.create(
            year=CurrentPackYearFactory(),
            ordering_opens=now - timezone.timedelta(days=30),
            ordering_closes=now - timezone.timedelta(days=1),
            delivery_available=today,
            prize_window_opens=today,
            prize_window_closes=today,
        )
        self.prize = Prize.objects.create(
            name="Camp Chair",
            points=5,
            value=decimal.Decimal("25.00"),
            campaign=self.campaign,
        )
        Quota.objects.create(campaign=self.campaign, den=self.scout.current_den, target=decimal.Decimal("500.00"))
        self.client.force_login(self.adult)

    def _update_selection(self, action="add"):
        return self.client.post(
            reverse("campaigns:api_update_prize_selection"),
            data=json.dumps({"action": action, "prize": self.prize.pk, "cub": str(self.scout.pk)}),
            content_type="application/json",
        )

    def _prize_nav_is_visible(self):
        response = self.client.get(reverse("pages:home"))
        return "Prize Selection" in [
            item["label"]
            for item in response.context["navbar_items"]
            if item["kind"] == "dropdown"
            for item in item["items"]
        ]

    def test_prize_selection_is_available_during_window(self):
        self.assertTrue(self._prize_nav_is_visible())

        response = self._update_selection()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            PrizeSelection.objects.filter(campaign=self.campaign, prize=self.prize, cub=self.scout).exists()
        )

    def test_prize_selection_is_visible_but_rejected_before_window(self):
        self.campaign.prize_window_opens = timezone.localdate() + timezone.timedelta(days=1)
        self.campaign.prize_window_closes = timezone.localdate() + timezone.timedelta(days=2)
        self.campaign.save()

        self.assertTrue(self._prize_nav_is_visible())
        page_response = self.client.get(reverse("campaigns:prize_selection"))

        response = self._update_selection()

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Prize selection is not currently available.")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PrizeSelection.objects.exists())

    def test_prize_selection_is_visible_but_rejected_after_window(self):
        self.campaign.prize_window_opens = timezone.localdate() - timezone.timedelta(days=2)
        self.campaign.prize_window_closes = timezone.localdate() - timezone.timedelta(days=1)
        self.campaign.save()

        self.assertTrue(self._prize_nav_is_visible())

        response = self._update_selection()

        self.assertEqual(response.status_code, 403)
        self.assertFalse(PrizeSelection.objects.exists())
