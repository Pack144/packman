# Generated by Django 3.2.4 on 2021-06-22 06:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calendars', '0003_auto_20210603_1701'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='packyear',
            options={'get_latest_by': 'start_date', 'ordering': ('-start_date',), 'verbose_name': 'pack year', 'verbose_name_plural': 'pack years'},
        ),
    ]
