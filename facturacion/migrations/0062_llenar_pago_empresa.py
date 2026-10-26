from django.db import migrations
from django.db.models import OuterRef, Subquery


def llenar_empresa_en_pagos(apps, schema_editor):
    """Los pagos ligados a una factura que quedaron sin empresa la toman de su factura."""
    Pago = apps.get_model("facturacion", "Pago")
    Factura = apps.get_model("facturacion", "Factura")
    empresa_de_factura = Factura.objects.filter(pk=OuterRef("factura_id")).values("empresa_id")[:1]
    Pago.objects.filter(empresa__isnull=True, factura__isnull=False).update(
        empresa=Subquery(empresa_de_factura)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0061_llenar_referencias_cortas"),
    ]

    operations = [
        migrations.RunPython(llenar_empresa_en_pagos, migrations.RunPython.noop),
    ]
