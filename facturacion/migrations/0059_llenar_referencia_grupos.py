from django.db import migrations


def llenar_referencias(apps, schema_editor):
    # Asigna referencia de pago a los grupos que ya existen (los nuevos la generan en save()).
    from catalogos.utils import generar_referencia_pago_propiedad

    Grupo = apps.get_model('facturacion', 'GrupoFacturacion')
    for g in Grupo.objects.filter(referencia_pago__isnull=True):
        for _ in range(10):
            ref = generar_referencia_pago_propiedad(g.cliente_id, 'G', g.nombre)
            if not Grupo.objects.filter(referencia_pago=ref).exists():
                g.referencia_pago = ref
                g.save(update_fields=['referencia_pago'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0058_grupofacturacion_referencia_pago'),
    ]

    operations = [
        migrations.RunPython(llenar_referencias, migrations.RunPython.noop),
    ]
