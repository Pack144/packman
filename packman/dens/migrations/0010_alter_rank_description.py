# Generated by Django 3.2.15 on 2022-10-20 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dens', '0009_alter_rank_rank'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rank',
            name='description',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
