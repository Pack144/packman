from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import PackYearFactory
from packman.campaigns.models import Campaign, Category, Order, Prize, Product
from packman.membership.factories import ScoutFactory

User = get_user_model()


class CampaignFilterTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.previous_year = PackYearFactory(year=2025)
        cls.current_year = PackYearFactory(year=2026)
        cls.previous_campaign = cls.create_campaign(
            cls.previous_year, timezone.make_aware(timezone.datetime(2025, 9, 1))
        )
        cls.current_campaign = cls.create_campaign(
            cls.current_year, timezone.make_aware(timezone.datetime(2026, 9, 1))
        )

        cls.previous_order = Order.objects.create(campaign=cls.previous_campaign, seller=ScoutFactory())
        cls.current_order = Order.objects.create(campaign=cls.current_campaign, seller=ScoutFactory())

        cls.previous_prize = Prize.objects.create(name="Old prize", points=1, campaign=cls.previous_campaign)
        cls.current_prize = Prize.objects.create(name="New prize", points=1, campaign=cls.current_campaign)

        cls.category = Category.objects.create(name="Snacks")

        cls.previous_product = Product.objects.create(
            name="Old product", price=1, campaign=cls.previous_campaign, category=cls.category
        )
        cls.current_product = Product.objects.create(
            name="New product", price=1, campaign=cls.current_campaign, category=cls.category
        )

        cls.superuser = User.objects.create_superuser(email="admin@example.com", password="changeme123")  # nosec B106

    @staticmethod
    def create_campaign(year, ordering_opens):
        return Campaign.objects.create(
            year=year,
            ordering_opens=ordering_opens,
            ordering_closes=ordering_opens + timezone.timedelta(days=30),
            delivery_available=ordering_opens + timezone.timedelta(days=45),
            prize_window_opens=ordering_opens + timezone.timedelta(days=45),
            prize_window_closes=ordering_opens + timezone.timedelta(days=60),
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_order_changelist_defaults_to_latest_campaign(self):
        url = reverse("admin:campaigns_order_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = list(response.context["cl"].queryset)
        self.assertIn(self.current_order, object_list)
        self.assertNotIn(self.previous_order, object_list)

    def test_order_changelist_all_shows_every_campaign(self):
        url = reverse("admin:campaigns_order_changelist")
        response = self.client.get(url, {"campaign__id__exact": "all"})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = list(response.context["cl"].queryset)
        self.assertIn(self.current_order, object_list)
        self.assertIn(self.previous_order, object_list)

    def test_order_changelist_specific_campaign(self):
        url = reverse("admin:campaigns_order_changelist")
        response = self.client.get(url, {"campaign__id__exact": self.previous_campaign.pk})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = list(response.context["cl"].queryset)
        self.assertIn(self.previous_order, object_list)
        self.assertNotIn(self.current_order, object_list)

    def test_prize_changelist_defaults_to_latest_campaign(self):
        url = reverse("admin:campaigns_prize_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = list(response.context["cl"].queryset)
        self.assertIn(self.current_prize, object_list)
        self.assertNotIn(self.previous_prize, object_list)

    def test_product_changelist_defaults_to_latest_campaign(self):
        url = reverse("admin:campaigns_product_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = list(response.context["cl"].queryset)
        self.assertIn(self.current_product, object_list)
        self.assertNotIn(self.previous_product, object_list)

    def test_campaign_admin_pages_show_contextual_guidance(self):
        changelist_response = self.client.get(reverse("admin:campaigns_campaign_changelist"))
        change_response = self.client.get(reverse("admin:campaigns_campaign_change", args=[self.current_campaign.pk]))
        prize_point_response = self.client.get(reverse("admin:campaigns_prizepoint_changelist"))

        self.assertContains(change_response, "<strong>Note:</strong>", html=True)
        self.assertContains(change_response, "exactly seven weeks")
        self.assertContains(change_response, "should not be changed after the campaign starts")
        self.assertContains(change_response, '<li class="warning">')
        self.assertNotContains(change_response, "Duplicate campaign, quotas, and products")
        self.assertNotContains(change_response, "Delete selected campaigns")

        self.assertContains(changelist_response, "Starting a new campaign?")
        self.assertContains(changelist_response, 'class="messagelist" style="clear: both;"')
        self.assertContains(changelist_response, '<li class="info">')
        self.assertContains(changelist_response, "Duplicate campaign, quotas, and products")
        self.assertContains(changelist_response, "Orders are not copied")
        self.assertNotContains(changelist_response, "Delete selected campaigns")
        self.assertNotContains(changelist_response, "<strong>Note:</strong>", html=True)
        self.assertNotContains(changelist_response, "exactly seven weeks")
        self.assertLess(
            changelist_response.content.index(b'class="object-tools"'),
            changelist_response.content.index(b"Starting a new campaign?"),
        )

        self.assertContains(prize_point_response, 'class="help" style="clear: both;"')
        self.assertLess(
            prize_point_response.content.index(b'class="object-tools"'),
            prize_point_response.content.index(b"Prize Points define"),
        )
