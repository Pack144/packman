from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation

from packman.calendars.factories import CurrentPackYearFactory
from packman.campaigns.models import Campaign, Category, Product
from packman.membership.factories import ActiveScoutFactory, AdultFactory, FamilyFactory


class OrderCreationTest(TestCase):
    def setUp(self):
        self.pack_year = CurrentPackYearFactory()
        self.family = FamilyFactory()
        self.adult = AdultFactory(family=self.family, is_active=True)
        self.scout = ActiveScoutFactory(family=self.family)
        opens = timezone.make_aware(datetime.combine(self.pack_year.start_date, datetime.min.time()))
        closes = timezone.make_aware(datetime.combine(self.pack_year.end_date, datetime.min.time()))
        self.campaign = Campaign.objects.create(
            year=self.pack_year,
            ordering_opens=opens,
            ordering_closes=closes,
            delivery_available=self.pack_year.end_date,
            prize_window_opens=self.pack_year.start_date,
            prize_window_closes=self.pack_year.end_date,
        )
        category = Category.objects.create(name="Snacks")
        self.product = Product.objects.create(
            name="Popcorn",
            category=category,
            campaign=self.campaign,
            price="12.50",
        )
        self.client.force_login(self.adult)

    def test_validation_error_preserves_submitted_order_item_formset(self):
        response = self.client.post(
            reverse("campaigns:order_create"),
            {
                "name": "Test Customer",
                "email": "",
                "phone_number": "",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zipcode": "not-a-zip",
                "latitude": "",
                "longitude": "",
                "gps_accuracy": "",
                "donation": "",
                "notes": "",
                "seller": str(self.scout.pk),
                "date_paid": "",
                "date_delivered": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-product": str(self.product.pk),
                "items-0-quantity": "3",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("zipcode", response.context["customer_form"].errors)
        self.assertContains(response, "is-invalid", html=False)
        item_form = response.context["items_formset"].forms[0]
        self.assertEqual(item_form["product"].value(), str(self.product.pk))
        self.assertEqual(item_form["quantity"].value(), "3")

    def test_product_price_data_attribute_is_not_localized(self):
        self.product.price = "1234.56"
        self.product.save(update_fields=("price",))

        with translation.override("de"):
            response = self.client.get(reverse("campaigns:order_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="{self.product.pk}-price" data-price="1234.56"')
