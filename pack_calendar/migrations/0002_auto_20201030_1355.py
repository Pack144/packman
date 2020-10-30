# Generated by Django 2.2.16 on 2020-10-30 20:55

from django.db import migrations, models


def event_migration_prep(apps, schema_editor):
    Event = apps.get_model("pack_calendar", "Event")
    fields = ("location", )

    for field in fields:
        filter_param = {"{}__isnull".format(field): True}
        update_param = {field: ""}
        Event.objects.filter(**filter_param).update(**update_param)


def category_migration_prep(apps, schema_editor):
    Category = apps.get_model("pack_calendar", "Category")
    fields = ("color", "description", "icon")

    for field in fields:
        filter_param = {"{}__isnull".format(field): True}
        update_param = {field: ""}
        Category.objects.filter(**filter_param).update(**update_param)


class Migration(migrations.Migration):

    dependencies = [
        ('pack_calendar', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(event_migration_prep, migrations.RunPython.noop),
        migrations.RunPython(category_migration_prep, migrations.RunPython.noop),
    ]
