# Generated by Django 2.2.16 on 2020-10-30 20:55

from django.db import migrations, models


def postgres_migration_prep(apps, schema_editor):
    Committee = apps.get_model("committees", "Committee")
    fields = ("description",)

    for field in fields:
        filter_param = {"{}__isnull".format(field): True}
        update_param = {field: ""}
        Committee.objects.filter(**filter_param).update(**update_param)


class Migration(migrations.Migration):
    dependencies = [
        ("committees", "0003_auto_20200730_0934"),
    ]

    operations = [
        migrations.RunPython(postgres_migration_prep, migrations.RunPython.noop)
    ]
