# Generated by Django 2.2.14 on 2020-07-30 16:34

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Den',
            fields=[
                ('number', models.PositiveSmallIntegerField(help_text='The Den number', primary_key=True, serialize=False)),
                ('date_added', models.DateField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Den',
                'verbose_name_plural': 'Dens',
                'ordering': ['number'],
            },
        ),
        migrations.CreateModel(
            name='Rank',
            fields=[
                ('rank', models.PositiveSmallIntegerField(choices=[(1, 'Bobcat'), (2, 'Tiger'), (3, 'Wolf'), (4, 'Bear'), (5, 'Jr. Webelo'), (6, 'Sr. Webelo'), (7, 'Webelo'), (8, 'Arrow of Light')], unique=True)),
                ('description', models.CharField(blank=True, max_length=128, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_added', models.DateField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rank',
                'verbose_name_plural': 'Ranks',
                'ordering': ['rank'],
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('den', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scouts', to='dens.Den')),
            ],
            options={
                'verbose_name': 'Member',
                'verbose_name_plural': 'Members',
                'ordering': ['year_assigned', 'den', 'scout'],
            },
        ),
    ]
