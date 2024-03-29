# Generated by Django 3.2.7 on 2021-09-29 21:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dens', '0008_auto_20210720_1640'),
        ('campaigns', '0002_rename_quota_field_to_target'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='quota',
            options={'get_latest_by': 'campaign'},
        ),
        migrations.AddField(
            model_name='product',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True, verbose_name='wholesale cost'),
        ),
        migrations.AddField(
            model_name='product',
            name='msrp',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True, verbose_name='MSRP'),
        ),
        migrations.AlterField(
            model_name='order',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='campaigns.customer'),
        ),
        migrations.AlterField(
            model_name='order',
            name='donation',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6, null=True, verbose_name='donation'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='quantity',
            field=models.IntegerField(default=1, verbose_name='quantity'),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True, verbose_name='sell price'),
        ),
        migrations.AlterField(
            model_name='quota',
            name='den',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotas', to='dens.den'),
        ),
    ]
