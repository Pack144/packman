from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import PackYearFactory
from packman.campaigns.admin import CampaignFilter, OrderAdmin, SellerFilter
from packman.campaigns.models import Campaign, CampaignScout, Category, Customer, Order, Prize, Product
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
        self.assertContains(changelist_response, 'id="changelist-form"')
        self.assertContains(changelist_response, '<li class="info">')
        self.assertContains(changelist_response, "Duplicate campaign, quotas, and products")
        self.assertContains(changelist_response, "Orders are not copied")
        self.assertNotContains(changelist_response, "Delete selected campaigns")
        self.assertNotContains(changelist_response, "<strong>Note:</strong>", html=True)
        self.assertNotContains(changelist_response, "exactly seven weeks")
        self.assertContains(change_response, 'id="campaign_form"')
        self.assertContains(prize_point_response, "Prize Points define")
        self.assertContains(prize_point_response, 'id="changelist-form"')

    def test_campaign_admin_shows_scout_settings(self):
        CampaignScout.objects.create(campaign=self.current_campaign, scout=self.current_order.seller, exempt=True)

        response = self.client.get(reverse("admin:campaigns_campaign_change", args=[self.current_campaign.pk]))

        self.assertContains(response, "This Cub is not required to meet the campaign quota.")
        self.assertContains(response, "exempt")
        self.assertContains(response, 'name="scouts-0-exempt"')
        self.assertNotContains(response, "admin_inline_tooltips.js")
        self.assertNotContains(response, "admin_inline_tooltips.css")


class OrderSellerFilterAndSearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.previous_campaign = CampaignFilterTestCase.create_campaign(
            PackYearFactory(year=2025), timezone.make_aware(timezone.datetime(2025, 9, 1))
        )
        cls.current_campaign = CampaignFilterTestCase.create_campaign(
            PackYearFactory(year=2026), timezone.make_aware(timezone.datetime(2026, 9, 1))
        )
        cls.current_seller = ScoutFactory(first_name="Alice", nickname="Allie", last_name="Current")
        cls.previous_seller = ScoutFactory(first_name="Pat", last_name="Former")
        cls.non_seller = ScoutFactory(first_name="Nobody", last_name="Sold")
        cls.customer = Customer.objects.create(
            name="Grandma Moses", email="grandma@example.com", phone_number="+12065550123", address="12 Elm St"
        )
        cls.current_order = Order.objects.create(
            campaign=cls.current_campaign, seller=cls.current_seller, customer=cls.customer
        )
        cls.other_current_order = Order.objects.create(campaign=cls.current_campaign, seller=ScoutFactory())
        cls.previous_order = Order.objects.create(campaign=cls.previous_campaign, seller=cls.previous_seller)
        cls.superuser = User.objects.create_superuser(
            email="seller-admin@example.com", password="seller-filter-test"  # nosec B106
        )
        cls.url = reverse("admin:campaigns_order_changelist")

    def setUp(self):
        self.client.force_login(self.superuser)

    def seller_choices(self, response):
        seller_filter = next(spec for spec in response.context["cl"].filter_specs if isinstance(spec, SellerFilter))
        return {pk for pk, _ in seller_filter.lookup_choices}

    def test_seller_choices_default_to_latest_campaign_sellers(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        choices = self.seller_choices(response)
        self.assertIn(self.current_seller.pk, choices)
        self.assertNotIn(self.previous_seller.pk, choices)
        self.assertNotIn(self.non_seller.pk, choices)

    def test_seller_choices_follow_selected_campaign(self):
        specific = self.seller_choices(self.client.get(self.url, {"campaign__id__exact": self.previous_campaign.pk}))
        every = self.seller_choices(self.client.get(self.url, {"campaign__id__exact": "all"}))

        self.assertEqual(specific, {self.previous_seller.pk})
        self.assertIn(self.current_seller.pk, every)
        self.assertIn(self.previous_seller.pk, every)
        self.assertNotIn(self.non_seller.pk, every)

    def test_seller_filter_limits_orders_and_keeps_selected_seller_choice(self):
        response = self.client.get(self.url, {"seller__id__exact": self.previous_seller.pk})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(list(response.context["cl"].queryset), [])
        self.assertIn(self.previous_seller.pk, self.seller_choices(response))

        response = self.client.get(
            self.url, {"campaign__id__exact": "all", "seller__id__exact": self.current_seller.pk}
        )
        self.assertEqual(list(response.context["cl"].queryset), [self.current_order])

    def test_malformed_filter_values_redirect_instead_of_erroring(self):
        for params in ({"seller__id__exact": "not-a-uuid"}, {"campaign__id__exact": "not-a-number"}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
                self.assertIn("e=1", response.url)

    def test_unknown_seller_shows_no_orders(self):
        response = self.client.get(self.url, {"seller__id__exact": "00000000-0000-0000-0000-000000000000"})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(list(response.context["cl"].queryset), [])

    def test_search_matches_seller_and_customer_fields(self):
        for term in ("Alice", "Allie", "Current", "Grandma", "grandma@example.com", "2065550123", "Elm St"):
            with self.subTest(term=term):
                response = self.client.get(self.url, {"q": term})
                self.assertEqual(list(response.context["cl"].queryset), [self.current_order])

    def test_seller_choices_respect_admin_queryset_boundaries(self):
        with patch.object(
            OrderAdmin,
            "get_queryset",
            return_value=Order.objects.filter(pk=self.current_order.pk).calculate_total(),
        ):
            response = self.client.get(
                self.url, {"campaign__id__exact": "all", "seller__id__exact": self.previous_seller.pk}
            )

        self.assertEqual(self.seller_choices(response), {self.current_seller.pk})
        self.assertEqual(list(response.context["cl"].queryset), [])

    def test_search_preserves_campaign_seller_and_paid_filters(self):
        self.previous_order.customer = self.customer
        self.previous_order.save()
        response = self.client.get(self.url, {"q": "Grandma"})
        self.assertEqual(list(response.context["cl"].queryset), [self.current_order])

        response = self.client.get(
            self.url,
            {"q": "Grandma", "campaign__id__exact": "all", "seller__id__exact": self.previous_seller.pk},
        )
        self.assertEqual(list(response.context["cl"].queryset), [self.previous_order])

        response = self.client.get(self.url, {"q": "Grandma", "paid": "true"})
        self.assertEqual(list(response.context["cl"].queryset), [])

    def test_filter_form_preserves_search_and_other_filters_and_resets_pagination(self):
        response = self.client.get(self.url, {"q": "Grandma", "paid": "false", "p": "1"})
        self.assertContains(response, '<input type="hidden" name="q" value="Grandma">', html=True)
        self.assertContains(response, '<input type="hidden" name="paid" value="false">', html=True)
        self.assertNotContains(response, '<input type="hidden" name="p"')

    def test_staff_without_order_permission_cannot_access_orders_or_seller_choices(self):
        staff = User.objects.create_user(email="staff@example.com", _is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_campaign_dropdown_selects_latest_by_default(self):
        response = self.client.get(self.url)
        spec = next(spec for spec in response.context["cl"].filter_specs if isinstance(spec, CampaignFilter))
        form = next(spec.choices(response.context["cl"]))["form"]
        self.assertEqual(form[CampaignFilter.parameter_name].value(), str(self.current_campaign.pk))
        self.assertIn(("all", "All"), form.fields[CampaignFilter.parameter_name].choices)

    def test_empty_campaign_has_no_seller_choices_and_still_filters_orders(self):
        Order.objects.filter(campaign=self.current_campaign).delete()
        response = self.client.get(self.url)
        self.assertEqual(list(response.context["cl"].queryset), [])
        self.assertFalse(any(isinstance(spec, SellerFilter) for spec in response.context["cl"].filter_specs))

    def test_campaign_and_seller_filters_render_as_dropdowns(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'name="campaign__id__exact"')
        self.assertContains(response, 'name="seller__id__exact"')
        self.assertContains(response, 'id="filter-form"')
        self.assertContains(response, "unfold/js/select2.init.js")
        self.assertNotContains(response, "admin_dropdown_filter.js")
        self.assertContains(response, "select2.full")
        self.assertContains(response, "Search by seller name or customer name")

        for name in ("prize", "product"):
            with self.subTest(name=name):
                response = self.client.get(reverse(f"admin:campaigns_{name}_changelist"))
                self.assertContains(response, 'name="campaign__id__exact"')
                self.assertContains(response, 'id="filter-form"')
                self.assertNotContains(response, "admin_dropdown_filter.js")


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
