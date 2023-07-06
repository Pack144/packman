import datetime

from django.test import TestCase
from django.utils import timezone

from packman.calendars.models import Category, Event, PackYear


class PackYearTestCase(TestCase):
    def test_dunder_str_matching_calendar_year(self):
        year = PackYear.objects.create(
            year=2020,
            start_date=datetime.date(
                year=2020,
                month=1,
                day=1,
            ),
            end_date=datetime.date(year=2020, month=12, day=31),
        )

        self.assertEqual(str(year), "2020")

    def test_dunder_str_matching_fiscal_year(self):
        year = PackYear.objects.create(
            year=2020,
            start_date=datetime.date(
                year=2020,
                month=9,
                day=1,
            ),
            end_date=datetime.date(year=2021, month=8, day=31),
        )

        self.assertEqual(str(year), "2020-2021")


class CategoryTestCase(TestCase):
    def test_dunder_string(self):
        category = Category.objects.create(name="Test")

        self.assertEqual(str(category), "Test")


class EventTestCase(TestCase):
    def test_dunder_string(self):
        event = Event.objects.create(
            name="Test Event",
            start=datetime.datetime(
                year=2020, month=9, day=1, hour=18, minute=0, tzinfo=timezone.get_default_timezone()
            ),
            category=Category.objects.create(name="Test"),
        )

        self.assertEqual(str(event), "Test Event")
