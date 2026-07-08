"""
Populate the local database with fake data for development, using the
project's factory_boy factories (packman/*/factories.py).

Usage:
    uv run python manage.py shell < util/seed_dev_data.py
"""

import random

from packman.calendars.factories import CategoryFactory, CurrentPackYearFactory, EventFactory
from packman.dens.factories import CurrentMembershipFactory, DenFactory
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory
from packman.membership.models import Scout

random.seed(42)

print("Seeding dens...")
dens = [DenFactory(number=n) for n in range(1, 6)]

print("Seeding families, adults, and scouts...")
families = []
for _ in range(20):
    family = FamilyFactory()
    for _ in range(random.randint(1, 2)):  # nosec B311
        AdultFactory(family=family)
    for _ in range(random.randint(1, 2)):  # nosec B311
        scout = ScoutFactory(family=family, status=Scout.ACTIVE)
        CurrentMembershipFactory(scout=scout, den=random.choice(dens))  # nosec B311
    if random.random() < 0.25:  # nosec B311
        ScoutFactory(family=family, status=Scout.INACTIVE)
    families.append(family)

print("Seeding calendar categories and events...")
categories = [CategoryFactory() for _ in range(4)]
for category in categories:
    for _ in range(5):
        EventFactory(category=category, future=random.choice([True, False]))  # nosec B311

CurrentPackYearFactory()

print("Done.")
print(f"Families: {len(families)}")
print(f"Dens: {len(dens)}")
