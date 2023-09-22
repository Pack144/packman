import datetime

from django.test import TestCase
from django.utils import timezone

from packman.attendance.models import Attendance
from packman.calendars.models import Category, Event
from packman.membership.models import Member


class AttendanceTestCase(TestCase):
    def test_empty_create(self):
        event = Event.objects.create(
            name="Test Event1",
            start=datetime.datetime(
                year=2020, month=9, day=1, hour=18, minute=0, tzinfo=timezone.get_default_timezone()
            ),
            category=Category.objects.create(name="Test"),
        )

        attendance = Attendance.objects.create(
            event=event,
        )
        self.assertEqual(str(event), "Test Event1")
        self.assertEqual(str(attendance), "2020-09-01 18:00:00-04:56 Test Event1")

    def test_member_create(self):
        Member.objects.create(first_name="Test1", last_name="Member")
        Member.objects.create(first_name="Test2", last_name="Member")
        Member.objects.create(first_name="Test3", last_name="Member")

        event = Event.objects.create(
            name="Test Event2",
            start=datetime.datetime(
                year=2020, month=9, day=1, hour=18, minute=0, tzinfo=timezone.get_default_timezone()
            ),
            category=Category.objects.create(name="Test"),
        )

        self.a1 = Attendance.objects.create(
            event=event,
        )
        self.assertEqual(self.a1.members.count(), 0)
        self.a1.members.add(Member.objects.get(first_name="Test1", last_name="Member"))
        self.assertEqual(self.a1.members.count(), 1)
        self.a1.members.add(Member.objects.get(first_name="Test2", last_name="Member"))
        self.assertEqual(self.a1.members.count(), 2)
        self.assertEqual(str(event), "Test Event2")
