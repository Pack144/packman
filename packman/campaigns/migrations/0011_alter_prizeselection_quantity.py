# Generated by Django 3.2.8 on 2021-10-28 00:01

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0010_order_recorded_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prizeselection',
            name='quantity',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='quantity'),
        ),
    ]