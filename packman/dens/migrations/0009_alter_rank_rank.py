# Generated by Django 3.2.15 on 2022-10-05 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dens', '0008_auto_20210720_1640'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rank',
            name='rank',
            field=models.IntegerField(choices=[(1, 'Lion'), (2, 'Tiger'), (3, 'Wolf'), (4, 'Bear'), (5, 'Jr. Webelo'), (6, 'Sr. Webelo'), (7, 'Webelo'), (8, 'Arrow of Light')], unique=True),
        ),
    ]