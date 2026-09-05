from django.db import migrations

# Scouting America registration, tracked for the two groups that must hold one:
# every active Cub, and the Pack's Akela, Assistant Akelas and Den Leaders.
# Split in two the same way the medical form is, because a Requirement carries
# one audience. Seeded here rather than left to the admin because the slugs are
# load bearing -- they are the roster URL, and the templates key off the source.
DEFAULTS = [
    {
        "slug": "scouting-membership-cub",
        "name": "Scouting America Membership (Cub)",
        "applies_to": "CUB",
        "source": "SA_MEMBERSHIP",
        "description": (
            "Every active Cub must hold a current Scouting America membership. "
            "Recorded on the Cub as a membership ID and expiration date, and "
            "satisfied for as long as that date is in the future."
        ),
        "sort_order": 0,
    },
    {
        "slug": "scouting-membership-leader",
        "name": "Scouting America Membership (Leader)",
        "applies_to": "LEADER",
        "source": "SA_MEMBERSHIP",
        "description": (
            "Akelas, Assistant Akelas and Den Leaders must hold a current "
            "Scouting America membership. Recorded on the leader as a membership "
            "ID and expiration date, and satisfied for as long as that date is "
            "in the future."
        ),
        "sort_order": 10,
    },
]


def create_scouting_membership_requirements(apps, schema_editor):
    Requirement = apps.get_model("compliance", "Requirement")
    for defaults in DEFAULTS:
        Requirement.objects.get_or_create(slug=defaults["slug"], defaults=defaults)


def remove_scouting_membership_requirements(apps, schema_editor):
    """
    Remove only the seeds that nobody has recorded against, matching
    0002_seed_default_requirements. Rolling back must not discard the records
    leadership has already opened against these.
    """
    Requirement = apps.get_model("compliance", "Requirement")
    Requirement.objects.filter(
        slug__in=[defaults["slug"] for defaults in DEFAULTS],
        record__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0003_requirement_source"),
    ]

    operations = [
        migrations.RunPython(
            create_scouting_membership_requirements,
            reverse_code=remove_scouting_membership_requirements,
        ),
    ]
