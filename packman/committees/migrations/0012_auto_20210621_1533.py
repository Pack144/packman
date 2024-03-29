# Generated by Django 3.2.4 on 2021-06-21 22:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('committees', '0011_rename_is_staff_committee_are_staff'),
    ]

    operations = [
        migrations.AddField(
            model_name='committee',
            name='are_superusers',
            field=models.BooleanField(default=False, help_text='Designates that members of this committee have all permissions without explicitly assigning them.', verbose_name='superusers'),
        ),
        migrations.AddField(
            model_name='committee',
            name='permissions',
            field=models.ManyToManyField(blank=True, to='auth.Permission', verbose_name='permissions'),
        ),
    ]
