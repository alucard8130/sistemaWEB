from django.db import migrations, models


class Migration(migrations.Migration):
    """GESAC Campus: area (Liceo / IPC / Cafeteria) del gasto. Solo agrega una
    columna con valor vacio por defecto; no modifica datos existentes."""

    dependencies = [
        ('gastos', '0011_indice_pagogasto_fecha'),
    ]

    operations = [
        migrations.AddField(
            model_name='gasto',
            name='area_escuela',
            field=models.CharField(
                blank=True, default='', max_length=12,
                choices=[('liceo', 'Liceo'), ('ipc', 'IPC'), ('cafeteria', 'Cafetería')],
            ),
        ),
    ]
