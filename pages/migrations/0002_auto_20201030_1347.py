# Generated by Django 2.2.16 on 2020-10-30 20:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='title',
            field=models.CharField(blank=True, default='', max_length=256),
        ),
    ]
