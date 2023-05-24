import datetime

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
