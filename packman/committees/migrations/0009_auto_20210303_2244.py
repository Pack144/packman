# Generated by Django 3.1.7 on 2021-03-04 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("committees", "0008_auto_20210112_1221"),
    ]

    operations = [
        migrations.AlterField(
            model_name="committee",
            name="date_added",
            field=models.DateTimeField(auto_now_add=True, verbose_name="date added"),
        ),
        migrations.AlterField(
            model_name="membership",
            name="date_added",
            field=models.DateTimeField(auto_now_add=True, verbose_name="date added"),
        ),
    ]
