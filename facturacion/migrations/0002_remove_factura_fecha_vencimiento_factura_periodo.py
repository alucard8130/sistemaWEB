# Generated by Django 5.2.1 on 2025-06-04 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='factura',
            name='fecha_vencimiento',
        ),
        migrations.AddField(
            model_name='factura',
            name='periodo',
            field=models.DateField(blank=True, null=True),
        ),
    ]
