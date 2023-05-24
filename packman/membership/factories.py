import random
import secrets
import string

import factory
from factory.faker import faker

from packman.membership.models import Adult, Family, Member, Scout

fake = faker.Faker()


class FamilyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Family


class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    gender = factory.Iterator(Member.GENDER_CHOICES, getter=lambda c: c[0])

    @factory.lazy_attribute
    def first_name(self):
        if self.gender == Member.MALE:
            return fake.first_name_male()
        elif self.gender == Member.FEMALE:
            return fake.first_name_female()
        else:
            return fake.first_name_nonbinary()

    last_name = factory.Faker("last_name")


class AdultFactory(MemberFactory):
    class Meta:
        model = Adult

    @factory.lazy_attribute
    def email(self):
        return f"{self.first_name[0]}{self.last_name}@{fake.domain_name()}"

    @factory.lazy_attribute
    def password(self):
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(20))

    family = factory.SubFactory(FamilyFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default `_create` with our custom call."""
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class ScoutFactory(MemberFactory):
    class Meta:
        model = Scout

    family = factory.SubFactory(FamilyFactory)
    status = Scout.ACTIVE


class ActiveScoutFactory(ScoutFactory):
    den_memberships = factory.RelatedFactory(
        "packman.dens.factories.CurrentMembershipFactory",
        factory_related_name="scout",
    )


class CompleteFamilyFactory(FamilyFactory):
    @factory.post_generation
    def adults(obj, create, extracted, **kwargs):
        if not create:
            # Build, not create related
            return

        for _ in range(extracted or random.randint(1, 2)):  # nosec: B311
            AdultFactory(family=obj)

    @factory.post_generation
    def inactive_children(obj, create, extracted, **kwargs):
        if not create:
            # Build, not create related
            return

        if extracted:
            for _ in range(extracted):
                ScoutFactory(family=obj)

    @factory.post_generation
    def active_children(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for _ in range(extracted):
                ActiveScoutFactory(family=obj)
