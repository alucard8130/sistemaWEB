# Generated by Django 5.2.1 on 2025-06-04 17:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0002_alter_cliente_unique_together'),
        ('locales', '0004_alter_localcomercial_cliente'),
    ]

    operations = [
        migrations.AlterField(
            model_name='localcomercial',
            name='cliente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='clientes.cliente'),
        ),
    ]
