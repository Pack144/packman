# Generated by Django 3.2.21 on 2023-09-22 23:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0010_alter_family_name_alter_family_pack_comments_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='member_id',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Member ID'),
        ),
    ]
