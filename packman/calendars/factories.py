import datetime
import random

from django.utils import timezone

import factory
from factory.faker import faker

from packman.calendars.models import Category, Event, PackYear

fake = faker.Faker()


class PackYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PackYear
        django_get_or_create = ("year",)

    class Params:
        follows_calendar = False

    year = fake.random_int(min=1900, max=timezone.now().year + 3)

    @factory.lazy_attribute
    def start_date(self):
        if self.follows_calendar:
            return datetime.date(year=self.year, month=1, day=1)
        else:
            return fake.date_object().replace(year=self.year)

    @factory.lazy_attribute
    def end_date(self):
        return self.start_date.replace(year=self.start_date.year + 1) - datetime.timedelta(days=1)


class CurrentPackYearFactory(PackYearFactory):
    class Params:
        follows_calendar = True
        django_get_or_create = ("year",)

    year = timezone.now().year


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("name",)

    @factory.lazy_attribute
    def name(self):
        return fake.text(max_nb_chars=32).rstrip(".")


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    class Params:
        future = True

    @factory.lazy_attribute
    def name(self):
        return fake.text(max_nb_chars=64).rstrip(".")

    @factory.lazy_attribute
    def start(self):
        if self.future:
            start_time = fake.date_time_this_year(tzinfo=timezone.get_current_timezone(), before_now=0)
        else:
            start_time = fake.date_time_this_year(tzinfo=timezone.get_current_timezone(), after_now=0)
        start_time = start_time.replace(minute=random.choice([0, 15, 30, 45]), second=0)  # nosec: B311
        return start_time

    @factory.lazy_attribute
    def end(self):
        return self.start + timezone.timedelta(hours=1)

    category = factory.SubFactory(CategoryFactory)
