# Generated by Django 3.2.4 on 2021-07-23 22:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0002_messagerecipient_distros'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messagedistribution',
            name='delivery',
            field=models.CharField(choices=[('to', 'To'), ('cc', 'Cc')], default='to', max_length=3, verbose_name=''),
        ),
        migrations.AlterField(
            model_name='messagerecipient',
            name='delivery',
            field=models.CharField(choices=[('to', 'To'), ('cc', 'Cc')], default='to', max_length=3, verbose_name=''),
        ),
    ]
