# Generated by Django 2.2.17 on 2020-11-03 21:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pack_calendar', '0005_auto_20201103_1356'),
        ('post_office', '0003_delete_message'),
    ]

    operations = [
        migrations.DeleteModel(
            name='GroupMailbox',
        ),
    ]
