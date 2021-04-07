# Generated by Django 2.2.17 on 2020-11-03 21:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0011_auto_20201103_1307"),
    ]

    operations = [
        migrations.AlterField(
            model_name="page",
            name="include_in_nav",
            field=models.BooleanField(
                default=False,
                help_text="Checking this option will add this page to the site's menu bar. Not used for standard pages (e.g. Home, About, Sign-up, etc.)",
                verbose_name="Include in navigation",
            ),
        ),
    ]
