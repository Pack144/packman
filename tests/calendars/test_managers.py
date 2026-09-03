import datetime

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from packman.calendars.models import PackYear


class PackYearTestCase(TestCase):
    now = timezone.now()

    @override_settings(PACK_YEAR_BEGIN_MONTH=1, PACK_YEAR_BEGIN_DAY=1)
    def test_create_following_calendar_year(self):
        year = PackYear.objects.create(year=2020)

        self.assertEqual(str(year), "2020")
        self.assertEqual(year.year, 2020)
        self.assertEqual(year.start_date.date(), datetime.date(year=2020, month=1, day=1))
        self.assertEqual(year.end_date.date(), datetime.date(year=2020, month=12, day=31))

    @override_settings(PACK_YEAR_BEGIN_MONTH=9, PACK_YEAR_BEGIN_DAY=1)
    def test_create_not_following_calendar_year(self):
        year = PackYear.objects.create(year=2020)

        self.assertEqual(str(year), "2019-2020")
        self.assertEqual(year.year, 2020)
        self.assertEqual(year.start_date.date(), datetime.date(year=2019, month=9, day=1))
        self.assertEqual(year.end_date.date(), datetime.date(year=2020, month=8, day=31))


class CurrentPackYearTestCase(TestCase):
    def setUp(self):
        # A migration default creates a pack year when the test database is
        # built; clear it so each case controls exactly which years exist.
        PackYear.objects.all().delete()
        cache.clear()

    def test_returns_the_year_covering_today(self):
        now = timezone.now()
        year = PackYear.objects.create(
            year=now.year, start_date=now - datetime.timedelta(days=30), end_date=now + datetime.timedelta(days=30)
        )

        self.assertEqual(PackYear.objects.current(), year)

    def test_still_raises_when_overlapping_years_cover_today(self):
        """
        Overlapping years should not exist. If one is entered by hand anyway,
        current() should raise rather than silently guess which one is right.
        """
        now = timezone.now()
        PackYear.objects.create(
            year=now.year, start_date=now - datetime.timedelta(days=300), end_date=now + datetime.timedelta(days=60)
        )
        PackYear.objects.create(
            year=now.year + 1,
            start_date=now - datetime.timedelta(days=10),
            end_date=now + datetime.timedelta(days=355),
        )

        with self.assertRaises(PackYear.MultipleObjectsReturned):
            PackYear.objects.current()

    def test_still_raises_when_no_year_covers_today(self):
        now = timezone.now()
        PackYear.objects.create(
            year=now.year - 5,
            start_date=now - datetime.timedelta(days=800),
            end_date=now - datetime.timedelta(days=500),
        )

        with self.assertRaises(PackYear.DoesNotExist):
            PackYear.objects.current()
