# Generated by Django 2.2.14 on 2020-07-30 16:34

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import polls.models
import tinymce.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('membership', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Choice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice_text', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.CharField(max_length=200)),
                ('description', tinymce.models.HTMLField(blank=True, null=True)),
                ('poll_opens', models.DateTimeField(blank=True, default=django.utils.timezone.now, verbose_name='poll opens')),
                ('poll_closes', models.DateTimeField(blank=True, default=polls.models.two_weeks_hence, verbose_name='poll closes')),
                ('is_anonymous', models.BooleanField(default=False, verbose_name='anonymous')),
                ('is_editable', models.BooleanField(default=True, verbose_name='editable')),
            ],
            options={
                'ordering': ('-poll_closes',),
            },
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('choice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.Choice')),
                ('family', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='membership.Family')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.Question')),
            ],
        ),
        migrations.AddField(
            model_name='choice',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.Question'),
        ),
    ]
