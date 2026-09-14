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
        self.assertContains(
            change_response,
            'The "Sales open" date anchors consecutive seven-day leaderboard and weekly report windows',
        )
        self.assertContains(change_response, "Wednesday at 5:00 PM")
        self.assertContains(change_response, "Wednesday 6:00 PM close")
        self.assertContains(change_response, "only one hour of orders")
        self.assertContains(
            change_response, "Changing Sales open after orders have started shifts every weekly window"
        )
        self.assertNotContains(change_response, "exactly seven weeks")
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


class CopyToLatestCampaignAdminActionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.source_campaign = cls.create_campaign(
            PackYearFactory(year=2025),
            now - timezone.timedelta(days=365),
        )
        cls.latest_campaign = cls.create_campaign(
            PackYearFactory(year=2026),
            now + timezone.timedelta(days=30),
        )
        cls.category = Category.objects.create(name="Snacks")
        cls.superuser = User.objects.create_superuser(
            email="copy-admin@example.com", password="password"  # nosec B106
        )

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

    def run_action(self, model_name, action, object_pk):
        url = reverse(f"admin:campaigns_{model_name}_changelist")
        return self.client.post(
            f"{url}?campaign__id__exact=all",
            {"action": action, "_selected_action": [object_pk]},
        )

    def test_duplicate_prizes_copies_to_future_latest_campaign_without_mutating_source(self):
        source = Prize.objects.create(
            name="Camping chair",
            points=12,
            value="24.99",
            url="https://example.com/chair",
            campaign=self.source_campaign,
        )
        source_pk = source.pk

        self.assertIsNone(Campaign.objects.current())
        response = self.run_action("prize", "duplicate_prizes", source_pk)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        source.refresh_from_db()
        self.assertEqual(source.pk, source_pk)
        self.assertEqual(source.campaign, self.source_campaign)
        copied = Prize.objects.exclude(pk=source_pk).get()
        self.assertEqual(copied.campaign, self.latest_campaign)
        self.assertEqual(copied.name, source.name)
        self.assertEqual(copied.points, source.points)
        self.assertEqual(copied.value, source.value)
        self.assertEqual(copied.url, source.url)

    def test_duplicate_products_copies_to_future_latest_campaign_without_mutating_source(self):
        source = Product.objects.create(
            name="Caramel corn",
            description="A classic",
            category=self.category,
            msrp="20.00",
            price="15.00",
            cost="8.00",
            weight="12.0",
            unit=Product.WeightUnit.OUNCE,
            sort_order=1,
            campaign=self.source_campaign,
        )
        source_pk = source.pk

        self.assertIsNone(Campaign.objects.current())
        response = self.run_action("product", "duplicate_products", source_pk)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        source.refresh_from_db()
        self.assertEqual(source.pk, source_pk)
        self.assertEqual(source.campaign, self.source_campaign)
        copied = Product.objects.exclude(pk=source_pk).get()
        self.assertEqual(copied.campaign, self.latest_campaign)
        self.assertEqual(copied.name, source.name)
        self.assertEqual(copied.description, source.description)
        self.assertEqual(copied.category, source.category)
        self.assertEqual(copied.msrp, source.msrp)
        self.assertEqual(copied.price, source.price)
        self.assertEqual(copied.cost, source.cost)
        self.assertEqual(copied.weight, source.weight)
        self.assertEqual(copied.unit, source.unit)
        self.assertEqual(copied.sort_order, source.sort_order)
