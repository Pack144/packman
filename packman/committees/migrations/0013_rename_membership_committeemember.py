# Generated by Django 3.2.4 on 2021-06-22 06:42

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dens', '0007_auto_20210603_1643'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('calendars', '0004_alter_packyear_options'),
        ('committees', '0012_auto_20210621_1533'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Membership',
            new_name='CommitteeMember',
        ),
    ]
