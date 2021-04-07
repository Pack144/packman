# Generated by Django 3.1.5 on 2021-01-12 19:22

from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("address_book", "0007_auto_20210111_1720"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="VenueType",
            new_name="Category",
        ),
        migrations.AlterModelOptions(
            name="category",
            options={
                "ordering": ["type"],
                "verbose_name": "category",
                "verbose_name_plural": "categories",
            },
        ),
    ]
