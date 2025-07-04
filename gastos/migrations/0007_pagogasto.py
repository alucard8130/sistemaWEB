# Generated by Django 5.2.1 on 2025-06-12 05:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0006_gasto_estatus_alter_gasto_comprobante'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PagoGasto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_pago', models.DateField()),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('forma_pago', models.CharField(choices=[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia'), ('cheque', 'Cheque'), ('tarjeta', 'Tarjeta')], default='efectivo', max_length=30)),
                ('referencia', models.CharField(blank=True, max_length=100, null=True)),
                ('gasto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagos', to='gastos.gasto')),
                ('registrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha_pago'],
            },
        ),
    ]
