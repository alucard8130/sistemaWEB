from django.db import migrations, models


class Migration(migrations.Migration):
    """Índice de rendimiento en PagoGasto.fecha_pago (no modifica datos)."""

    dependencies = [
        ('gastos', '0010_gasto_monto_base_gasto_monto_iva'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='pagogasto',
            index=models.Index(fields=['fecha_pago'], name='pagogasto_fecha_pago_idx'),
        ),
    ]
