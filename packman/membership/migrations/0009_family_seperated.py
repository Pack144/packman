# Generated by Django 3.2.8 on 2021-10-19 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0008_auto_20210720_1640'),
    ]

    operations = [
        migrations.AddField(
            model_name='family',
            name='seperated',
            field=models.BooleanField(default=False, help_text='Check this box if the parents in this family have legally seperated.', verbose_name='parents seperated'),
        ),
    ]