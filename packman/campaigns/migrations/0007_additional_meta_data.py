# Generated by Django 3.2.7 on 2021-10-06 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0006_prize_image'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ('-date_added',), 'verbose_name': 'Order', 'verbose_name_plural': 'Orders'},
        ),
        migrations.AlterField(
            model_name='customer',
            name='email',
            field=models.EmailField(blank=True, help_text='If provided, we will email you a receipt for this order. We do not share this information with anyone, including BSA.', max_length=254, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='name',
            field=models.CharField(help_text='The name to place on the order', max_length=150, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='order',
            name='donation',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Would you care to make monetary donation to the Pack?', max_digits=6, null=True, verbose_name='donation'),
        ),
        migrations.AlterField(
            model_name='order',
            name='notes',
            field=models.TextField(blank=True, help_text='Use the notes field to keep reminders such as "It\'s okay to leave nuts in the milkbox"', verbose_name='notes'),
        ),
    ]
