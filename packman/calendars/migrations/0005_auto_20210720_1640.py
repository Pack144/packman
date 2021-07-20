# Generated by Django 3.2.4 on 2021-07-20 23:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendars', '0004_alter_packyear_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='event',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
    ]
