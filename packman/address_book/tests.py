from django.test import TestCase

from .models import Address, Category, PhoneNumber, Venue


class AddressModelTests(TestCase):
    def test_valid_single_line_address(self):
        address = Address.objects.create(street="123 Main St.", city="Seattle", state="WA", zip_code="98101")

        self.assertEqual(address.street, "123 Main St.")
        self.assertEqual(address.street2, "")
        self.assertEqual(address.city, "Seattle")
        self.assertEqual(address.state, "WA")
        self.assertEqual(address.zip_code, "98101")
        self.assertEqual(str(address), "123 Main St., Seattle, WA, 98101")
        self.assertTrue(address.published)
        self.assertIsNotNone(address.date_added)
        self.assertIsNotNone(address.last_updated)

    def test_valid_multi_line_address(self):
        address = Address.objects.create(
            street="321 Main St.", street2="Suite 100", city="Seattle", state="WA", zip_code="98101"
        )

        self.assertEqual(address.street2, "Suite 100")
        self.assertEqual(str(address), "321 Main St. Suite 100, Seattle, WA, 98101")


class PhoneNumberModelTests(TestCase):
    def test_valid_phone(self):
        phone = PhoneNumber.objects.create(number="206-555-1212")

        self.assertEqual(phone.number, "+12065551212")
        self.assertEqual(str(phone), "(206) 555-1212")
        self.assertTrue(phone.published)
        self.assertIsNotNone(phone.date_added)
        self.assertIsNotNone(phone.last_updated)


class VenueModelTests(TestCase):
    def test_valid_venue(self):
        venue = Venue.objects.create(name="Example School")

        self.assertEqual(venue.name, "Example School")
        self.assertEqual(str(venue), "Example School")
        self.assertIsNotNone(venue.date_added)
        self.assertIsNotNone(venue.last_updated)


class CategoryModelTests(TestCase):
    def test_valid_category(self):
        category = Category.objects.create(name="foo")

        self.assertEqual(category.name, "foo")
        self.assertEqual(str(category), "foo")
        self.assertIsNotNone(category.date_added)
        self.assertIsNotNone(category.last_updated)
