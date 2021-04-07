# Generated by Django 3.1.4 on 2020-12-18 00:41

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0013_auto_20201106_1646"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="page",
            name="created_on",
        ),
        migrations.AddField(
            model_name="page",
            name="date_added",
            field=models.DateTimeField(auto_now=True, verbose_name="date added"),
        ),
        migrations.AlterField(
            model_name="contentblock",
            name="date_added",
            field=models.DateTimeField(auto_now=True, verbose_name="date added"),
        ),
        migrations.AlterField(
            model_name="contentblock",
            name="last_updated",
            field=models.DateTimeField(auto_now=True, verbose_name="last updated"),
        ),
        migrations.AlterField(
            model_name="contentblock",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="UUID",
            ),
        ),
        migrations.AlterField(
            model_name="page",
            name="last_updated",
            field=models.DateTimeField(auto_now=True, verbose_name="last updated"),
        ),
        migrations.AlterField(
            model_name="page",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
                unique=True,
                verbose_name="UUID",
            ),
        ),
    ]
