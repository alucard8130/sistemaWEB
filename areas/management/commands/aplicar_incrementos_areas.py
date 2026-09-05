from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from areas.models import AreaComun, HistorialIncrementoArea


class Command(BaseCommand):
    help = "Aplica incrementos automaticos de renta a las areas comunes cuyo aniversario de contrato sea hoy"

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        areas = AreaComun.objects.filter(
            activo=True,
            tipo_incremento='porcentaje_fijo',
            fecha_inicial__isnull=False,
            porcentaje_incremento__isnull=False,
        )

        aplicados = 0
        for area in areas:
            if hoy.year <= area.fecha_inicial.year:
                continue

            if area.fecha_inicial.month != hoy.month or area.fecha_inicial.day != hoy.day:
                continue

            if area.fecha_ultimo_incremento and area.fecha_ultimo_incremento.year == hoy.year:
                continue

            cuota_anterior = area.cuota
            factor = Decimal('1') + (area.porcentaje_incremento / Decimal('100'))  # noqa: FURB157
            cuota_nueva = (cuota_anterior * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            area.cuota = cuota_nueva
            area.fecha_ultimo_incremento = hoy
            area.save(update_fields=['cuota', 'fecha_ultimo_incremento'])

            HistorialIncrementoArea.objects.create(
                area=area,
                cuota_anterior=cuota_anterior,
                cuota_nueva=cuota_nueva,
                porcentaje_aplicado=area.porcentaje_incremento,
            )
            aplicados += 1

        self.stdout.write(self.style.SUCCESS(f"Incrementos aplicados: {aplicados}"))