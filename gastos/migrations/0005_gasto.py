# Generated by Django 5.2.1 on 2025-06-10 23:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empleados', '0001_initial'),
        ('empresas', '0001_initial'),
        ('gastos', '0004_tipogasto'),
        ('proveedores', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Gasto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.CharField(blank=True, max_length=255)),
                ('fecha', models.DateField()),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('comprobante', models.FileField(blank=True, null=True, upload_to='comprobantes/')),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('empleado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='empleados.empleado')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa')),
                ('proveedor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='proveedores.proveedor')),
                ('tipo_gasto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gastos.tipogasto')),
            ],
        ),
    ]
