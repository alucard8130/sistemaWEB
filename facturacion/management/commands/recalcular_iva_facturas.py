# ============================================================
# Colócalo en: facturacion/management/commands/recalcular_iva_facturas.py
# (crea las carpetas management/ y management/commands/ si no
# existen, cada una con su __init__.py vacío)
#
# Uso:
#   python manage.py recalcular_iva_facturas
# ============================================================

from django.core.management.base import BaseCommand

from facturacion.models import Factura  # ajusta el import a tu ruta real
from facturacion.utils import calcular_iva_factura  # ajusta el import a tu ruta real


class Command(BaseCommand):
    help = "Recalcula monto_base y monto_iva de todas las facturas existentes en la base."

    def handle(self, *args, **options):
        facturas = Factura.objects.all()
        total = facturas.count()
        actualizadas = 0
        lote = []
        TAMANO_LOTE = 500

        self.stdout.write(f"Recalculando {total} factura(s)...")

        for factura in facturas.iterator(chunk_size=500):
            monto_base, monto_iva = calcular_iva_factura(factura.monto, factura.tipo_cuota)
            factura.monto_base = monto_base
            factura.monto_iva = monto_iva
            lote.append(factura)
            actualizadas += 1

            if len(lote) >= TAMANO_LOTE:
                Factura.objects.bulk_update(lote, ["monto_base", "monto_iva"])
                self.stdout.write(f"  {actualizadas}/{total} procesadas...")
                lote = []

        if lote:
            Factura.objects.bulk_update(lote, ["monto_base", "monto_iva"])

        self.stdout.write(
            self.style.SUCCESS(f"✅ {actualizadas} factura(s) recalculada(s) correctamente.")
        )
