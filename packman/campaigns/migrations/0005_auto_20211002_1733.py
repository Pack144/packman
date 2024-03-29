# Generated by Django 3.2.7 on 2021-10-03 00:33

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0004_auto_20211001_1415'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='email',
            field=models.EmailField(blank=True, help_text='We will only use your email address to contact you about your order.', max_length=254, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, help_text='We would use this only if we needed to talk to you about your order.', max_length=128, region='US', verbose_name='phone number'),
        ),
    ]
