import random

from django.db import migrations


def llenar_referencias_cortas(apps, schema_editor):
    """Asigna referencia corta (7 dígitos) a todos los locales, áreas y grupos existentes.
    Las referencias largas (referencia_pago) se conservan y siguen siendo reconocidas."""
    Local = apps.get_model('locales', 'LocalComercial')
    Area = apps.get_model('areas', 'AreaComun')
    Grupo = apps.get_model('facturacion', 'GrupoFacturacion')

    usadas = set()
    for Modelo in (Local, Area, Grupo):
        usadas.update(Modelo.objects.exclude(referencia_corta__isnull=True).values_list('referencia_corta', flat=True))

    def nueva():
        for _ in range(100):
            ref = str(random.randint(1000000, 9999999))
            if ref not in usadas:
                usadas.add(ref)
                return ref
        raise ValueError("No se pudo generar referencia corta única.")

    for Modelo in (Local, Area, Grupo):
        for obj in Modelo.objects.filter(referencia_corta__isnull=True).iterator():
            obj.referencia_corta = nueva()
            obj.save(update_fields=['referencia_corta'])


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0060_grupofacturacion_referencia_corta'),
        ('locales', '0021_localcomercial_referencia_corta'),
        ('areas', '0028_areacomun_referencia_corta'),
    ]

    operations = [
        migrations.RunPython(llenar_referencias_cortas, migrations.RunPython.noop),
    ]
