import calendar

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from arrendamientos.models import ContratoArea


class Command(BaseCommand):
    help = (
        "Extiende mes a mes la fecha_fin de los contratos vencidos que "
        "nadie ha renovado ni terminado -- los marca como "
        "'vencido_ocupado' (mes a mes) y sigue extendiendolos "
        "indefinidamente hasta que se renueven o se terminen."
    )

    def handle(self, *args, **options):
        hoy = timezone.now().date()

        contratos_a_revisar = ContratoArea.objects.filter(
            estatus__in=['vigente', 'vencido_ocupado'],
            fecha_fin__lt=hoy,
        ).select_related('area')

        contador = 0
        for contrato in contratos_a_revisar:
            while contrato.fecha_fin < hoy:
                mes_siguiente = contrato.fecha_fin + relativedelta(months=1)
                ultimo_dia = calendar.monthrange(mes_siguiente.year, mes_siguiente.month)[1]
                contrato.fecha_fin = mes_siguiente.replace(day=ultimo_dia)

            contrato.estatus = 'vencido_ocupado'
            contrato.save(update_fields=['estatus', 'fecha_fin'])
            contrato.sincronizar_a_area()
            contador += 1

            self.stdout.write(
                f"  Area {contrato.area.numero}: extendido hasta {contrato.fecha_fin}"
            )

        self.stdout.write(self.style.SUCCESS(f"{contador} contrato(s) extendido(s)."))