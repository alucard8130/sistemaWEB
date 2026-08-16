# ============================================================
# Colócalo en: gastos/management/commands/recalcular_iva_gastos.py
# (crea las carpetas management/ y management/commands/ si no
# existen, cada una con su __init__.py vacío)
#
# Uso:
#   python manage.py recalcular_iva_gastos
# ============================================================

from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand

from gastos.models import Gasto  # ajusta el import a tu ruta real

IVA_TASA = Decimal("0.16")


class Command(BaseCommand):
    help = "Recalcula monto_base y monto_iva de todos los Gasto existentes en la base."

    def handle(self, *args, **options):
        gastos = Gasto.objects.select_related(
            "tipo_gasto", "tipo_gasto__subgrupo", "tipo_gasto__subgrupo__grupo"
        ).all()
        total = gastos.count()
        actualizados = 0
        lote = []
        TAMANO_LOTE = 500

        self.stdout.write(f"Recalculando {total} gasto(s)...")

        for gasto in gastos.iterator(chunk_size=500):
            if not gasto.tipo_gasto_id:
                # Gasto sin tipo asignado -- no se puede saber si es exento,
                # se deja tal cual sin tocar.
                continue

            monto = Decimal(str(gasto.monto))
            es_exento = gasto.tipo_gasto.subgrupo.grupo.es_exento_iva

            if es_exento:
                gasto.monto_base = monto
                gasto.monto_iva = Decimal("0")
            else:
                base = (monto / (Decimal("1") + IVA_TASA)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                gasto.monto_base = base
                gasto.monto_iva = monto - base

            lote.append(gasto)
            actualizados += 1

            if len(lote) >= TAMANO_LOTE:
                Gasto.objects.bulk_update(lote, ["monto_base", "monto_iva"])
                self.stdout.write(f"  {actualizados}/{total} procesados...")
                lote = []

        if lote:
            Gasto.objects.bulk_update(lote, ["monto_base", "monto_iva"])

        self.stdout.write(
            self.style.SUCCESS(f"✅ {actualizados} gasto(s) recalculado(s) correctamente.")
        )