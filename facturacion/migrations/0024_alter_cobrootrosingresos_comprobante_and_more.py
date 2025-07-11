# Generated by Django 5.2.1 on 2025-07-01 02:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0023_cobrootrosingresos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cobrootrosingresos',
            name='comprobante',
            field=models.FileField(blank=True, null=True, upload_to='comprobantes_oi/'),
        ),
        migrations.AlterField(
            model_name='facturaotrosingresos',
            name='cfdi',
            field=models.FileField(blank=True, max_length=255, null=True, upload_to='fact_sat_oi/'),
        ),
    ]
