# Generated by Django 2.2.17 on 2020-11-03 00:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0006_auto_20201030_1605'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ContentBlocks',
            new_name='ContentBlock',
        ),
        migrations.RemoveIndex(
            model_name='contentblock',
            name='pages_conte_title_43e30f_idx',
        ),
        migrations.AddIndex(
            model_name='contentblock',
            index=models.Index(fields=['title', 'published_on'], name='pages_conte_title_1776ce_idx'),
        ),
    ]