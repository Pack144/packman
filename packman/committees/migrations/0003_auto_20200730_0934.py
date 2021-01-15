# Generated by Django 2.2.14 on 2020-07-30 16:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import packman.calendars.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('calendars', '0001_initial'),
        ('committees', '0002_membership_den'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='committees', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='membership',
            name='year_served',
            field=models.ForeignKey(default=packman.calendars.models.PackYear.get_current_pack_year_year, on_delete=django.db.models.deletion.CASCADE, related_name='committee_memberships', to='calendars.PackYear'),
        ),
        migrations.AddField(
            model_name='committee',
            name='members',
            field=models.ManyToManyField(through='committees.Membership', to=settings.AUTH_USER_MODEL),
        ),
    ]