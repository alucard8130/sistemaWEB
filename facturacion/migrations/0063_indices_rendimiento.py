from django.db import migrations, models


class Migration(migrations.Migration):
    """Índices de rendimiento (solo crea índices; no modifica datos)."""

    dependencies = [
        ('facturacion', '0062_llenar_pago_empresa'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='factura',
            index=models.Index(fields=['empresa', 'estatus', 'fecha_vencimiento'], name='fac_emp_est_venc_idx'),
        ),
        migrations.AddIndex(
            model_name='factura',
            index=models.Index(fields=['fecha_emision'], name='fac_fecha_emision_idx'),
        ),
        migrations.AddIndex(
            model_name='pago',
            index=models.Index(fields=['fecha_pago'], name='pago_fecha_pago_idx'),
        ),
        migrations.AddIndex(
            model_name='cobrootrosingresos',
            index=models.Index(fields=['fecha_cobro'], name='cobro_oi_fecha_cobro_idx'),
        ),
    ]
