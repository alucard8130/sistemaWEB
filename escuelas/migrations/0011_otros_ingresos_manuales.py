import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """GESAC Campus -- otros ingresos capturados a mano: origen 'manual', tipo de
    ingreso (catalogo del usuario) y quien pago. Solo agrega columnas vacias."""

    dependencies = [
        ('escuelas', '0010_ingresoescuela_grado_grupo'),
        ('facturacion', '0063_indices_rendimiento'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ingresoescuela',
            name='origen',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                choices=[
                    ('cobranza', 'Reporte de Cobranza'),
                    ('fiserv', 'Plataforma Academic (Fiserv)'),
                    ('manual', 'Otro ingreso (captura manual)'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='ingresoescuela',
            name='tipo_otro_ingreso',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='ingresos_escuela', to='facturacion.tipootroingreso',
            ),
        ),
        migrations.AddField(
            model_name='ingresoescuela',
            name='pagador',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
