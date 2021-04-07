# Generated by Django 3.1.5 on 2021-01-14 18:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("address_book", "0011_auto_20210112_1129"),
        ("membership", "0004_auto_20201030_1531"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scout",
            name="school",
            field=models.ForeignKey(
                blank=True,
                help_text="Tell us what school your child attends. If your school isn't listed, tell us in the comments section.",
                limit_choices_to={"categories__name__icontains": "school"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="address_book.venue",
            ),
        ),
    ]
