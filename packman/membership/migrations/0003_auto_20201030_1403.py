# Generated by Django 2.2.16 on 2020-10-30 21:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0002_auto_20201030_1356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='family',
            name='name',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AlterField(
            model_name='family',
            name='pack_comments',
            field=models.TextField(blank=True, default='', help_text='Used by pack leadership to keep notes about a specific family. This information is not generally disclosed to members unless they are granted access to Membership.', verbose_name='Pack Comments'),
        ),
        migrations.AlterField(
            model_name='member',
            name='gender',
            field=models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Prefer not to say')], default='', max_length=1, verbose_name='Gender'),
        ),
        migrations.AlterField(
            model_name='member',
            name='middle_name',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Middle Name'),
        ),
        migrations.AlterField(
            model_name='member',
            name='nickname',
            field=models.CharField(blank=True, default='', help_text='If there is another name you prefer to be called, tell us and we will use it any time we refer to you on the website.', max_length=32, verbose_name='Nickname'),
        ),
        migrations.AlterField(
            model_name='member',
            name='pack_comments',
            field=models.TextField(blank=True, default='', help_text='Used by pack leadership to keep notes about a specific member. This information is not generally disclosed to the member unless they are granted access to Membership.', verbose_name='Pack Comments'),
        ),
        migrations.AlterField(
            model_name='member',
            name='slug',
            field=models.SlugField(blank=True, default='', unique=True),
        ),
        migrations.AlterField(
            model_name='member',
            name='suffix',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='Suffix'),
        ),
        migrations.AlterField(
            model_name='scout',
            name='member_comments',
            field=models.TextField(blank=True, default='', help_text='What other information should we consider when reviewing your application?', verbose_name='Comments'),
        ),
        migrations.AlterField(
            model_name='scout',
            name='reference',
            field=models.CharField(blank=True, default='', help_text='If you know someone who is already in the pack, you can tell us their name so we can credit them for referring you.', max_length=128, verbose_name='Referral(s)'),
        ),
    ]