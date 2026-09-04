from django.db import migrations

# The requirements the pack tracks today. Seeded here rather than in a
# management command so that a fresh install, a deploy, and the test database
# are all configured the same way without anyone having to remember a step.
DEFAULTS = [
    {
        "slug": "medical-form-cub",
        "name": "Medical Form (Cub)",
        "applies_to": "CUB",
        "sort_order": 20,
    },
    {
        "slug": "medical-form-adult",
        "name": "Medical Form (Adult)",
        "applies_to": "ADULT",
        "sort_order": 30,
    },
    {
        "slug": "pack-dues",
        "name": "Pack Dues",
        "applies_to": "FAMILY",
        "sort_order": 40,
    },
]


def create_default_requirements(apps, schema_editor):
    Requirement = apps.get_model("compliance", "Requirement")
    for defaults in DEFAULTS:
        Requirement.objects.get_or_create(slug=defaults["slug"], defaults=defaults)


def remove_default_requirements(apps, schema_editor):
    """
    Remove only the seeds that nobody has recorded against. Rolling a migration
    back must never discard the paperwork leadership has already collected.
    """
    Requirement = apps.get_model("compliance", "Requirement")
    Requirement.objects.filter(
        slug__in=[defaults["slug"] for defaults in DEFAULTS],
        record__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_requirements, reverse_code=remove_default_requirements),
    ]
