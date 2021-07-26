# Generated by Django 3.2.4 on 2021-07-20 23:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('address_book', '0013_auto_20210603_1626'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='category',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='distributionlist',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='phonenumber',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='venue',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, help_text='Date and time this entry was first added to the database.', verbose_name='created'),
        ),
    ]