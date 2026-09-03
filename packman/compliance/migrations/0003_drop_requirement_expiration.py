from django.db import migrations

# Requirements no longer expire. A record is satisfied for a pack year or it is
# not; anything needing renewal is asked for again in the next year's records,
# which the year foreign key already scopes.
#
# This drops collected expiration dates and cannot be undone by reversing the
# migration -- the reverse restores the columns, but not what was in them.


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0002_seed_default_requirements"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="requirementrecord",
            name="compliance__expires_f58263_idx",
        ),
        migrations.RemoveField(
            model_name="requirement",
            name="default_duration_days",
        ),
        migrations.RemoveField(
            model_name="requirement",
            name="tracks_expiration",
        ),
        migrations.RemoveField(
            model_name="requirementrecord",
            name="expires_on",
        ),
    ]
