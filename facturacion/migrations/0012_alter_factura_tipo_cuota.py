# Generated by Django 5.2.1 on 2025-06-10 03:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0011_factura_tipo_cuota'),
    ]

    operations = [
        migrations.AlterField(
            model_name='factura',
            name='tipo_cuota',
            field=models.CharField(choices=[('mantenimiento', 'Mantenimiento'), ('renta', 'Renta'), ('deposito garantia', 'Deposito Garantía'), ('servicios', 'Servicios'), ('extraordinaria', 'Extraordinaria'), ('penalidad', 'Penalidad'), ('publicidad', 'Publicidad')], max_length=20),
        ),
    ]
