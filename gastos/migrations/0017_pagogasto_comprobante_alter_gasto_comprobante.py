# Generated by Django 5.2.1 on 2025-07-01 03:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0016_alter_subgrupogasto_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagogasto',
            name='comprobante',
            field=models.FileField(blank=True, null=True, upload_to='comprobante_gastos/'),
        ),
        migrations.AlterField(
            model_name='gasto',
            name='comprobante',
            field=models.FileField(blank=True, null=True, upload_to='cfdi_gastos/'),
        ),
    ]
