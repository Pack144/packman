# Generated by Django 3.2.13 on 2022-04-22 22:12

from django.db import migrations, models


def update_status_for_previously_sent_messages(apps, schema_editor):
    Message = apps.get_model("mail", "Message")
    Message.objects.filter(date_sent__isnull=False).update(status="SENT")


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0009_alter_message_body'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('SENDING', 'Sending'), ('SENT', 'Sent'), ('FAILED', 'Failed')], default='DRAFT', editable=False, max_length=8, verbose_name='status'),
        ),
        migrations.RunPython(update_status_for_previously_sent_messages, reverse_code=migrations.RunPython.noop),
    ]
