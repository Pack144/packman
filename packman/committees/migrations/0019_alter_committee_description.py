# Generated by Django 4.2.3 on 2023-07-07 18:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("committees", "0018_alter_committeemember_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="committee",
            name="description",
            field=models.TextField(blank=True),
        ),
    ]
