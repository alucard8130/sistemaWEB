import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cobros_estado_cuenta', '0007_delete_traspasocuenta'),
        ('facturacion', '0059_llenar_referencia_grupos'),
    ]

    operations = [
        migrations.AddField(
            model_name='movimientoestadocuenta',
            name='propiedad_grupo',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='movimientos_estado_cuenta', to='facturacion.grupofacturacion',
            ),
        ),
        migrations.AlterField(
            model_name='movimientoestadocuenta',
            name='propiedad_tipo',
            field=models.CharField(
                blank=True, null=True, max_length=10,
                choices=[('local', 'Local Comercial'), ('area', 'Área Común'), ('grupo', 'Grupo de Facturación')],
            ),
        ),
    ]
