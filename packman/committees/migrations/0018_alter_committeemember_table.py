# Generated by Django 3.2.18 on 2023-03-10 20:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0017_auto_20210720_1640'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='committeemember',
            table='committees_committee_members',
        ),
    ]