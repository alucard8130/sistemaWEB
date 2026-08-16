# ============================================================
# Colócalo en: facturacion/management/commands/recalcular_iva_otros_ingresos.py
# (crea las carpetas management/ y management/commands/ si no
# existen, cada una con su __init__.py vacío -- si ya las creaste
# para recalcular_iva_facturas.py, solo agrega este archivo ahí)
#
# Uso:
#   python manage.py recalcular_iva_otros_ingresos
# ============================================================

from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand
from facturacion.models import FacturaOtrosIngresos  # ajusta el import a tu ruta real

IVA_TASA = Decimal("0.16")


class Command(BaseCommand):
    help = "Recalcula monto_base y monto_iva de todas las FacturaOtrosIngresos existentes en la base."

    def handle(self, *args, **options):
        facturas = FacturaOtrosIngresos.objects.all()
        total = facturas.count()
        actualizadas = 0
        lote = []
        TAMANO_LOTE = 500

        self.stdout.write(f"Recalculando {total} factura(s) de Otros Ingresos...")

        for factura in facturas.iterator(chunk_size=500):
            monto = Decimal(str(factura.monto))
            base = (monto / (Decimal("1") + IVA_TASA)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            factura.monto_base = base
            factura.monto_iva = monto - base
            lote.append(factura)
            actualizadas += 1

            if len(lote) >= TAMANO_LOTE:
                FacturaOtrosIngresos.objects.bulk_update(lote, ["monto_base", "monto_iva"])
                self.stdout.write(f"  {actualizadas}/{total} procesadas...")
                lote = []

        if lote:
            FacturaOtrosIngresos.objects.bulk_update(lote, ["monto_base", "monto_iva"])

        self.stdout.write(
            self.style.SUCCESS(f"✅ {actualizadas} factura(s) de Otros Ingresos recalculada(s) correctamente.")
        )
