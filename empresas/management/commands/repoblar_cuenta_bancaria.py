from django.core.management.base import BaseCommand, CommandError

from empresas.models import CuentaBancaria
from empresas.signals import poblar_cuenta_bancaria_inicial


class Command(BaseCommand):
    help = "Repuebla cuenta_bancaria en registros historicos de la empresa."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cuenta-id",
            type=int,
            required=True,
            help="ID de la cuenta bancaria que se asignara.",
        )
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="Sobrescribe cuenta_bancaria existente en los registros de la empresa.",
        )

    def handle(self, *args, **options):
        cuenta_id = options["cuenta_id"]
        forzar = options["forzar"]

        try:
            cuenta_bancaria = CuentaBancaria.objects.select_related("empresa").get(
                id=cuenta_id
            )
        except CuentaBancaria.DoesNotExist:
            raise CommandError(
                f"No existe la cuenta bancaria con id {cuenta_id}."
            )

        resumen = poblar_cuenta_bancaria_inicial(
            cuenta_bancaria,
            sobrescribir=forzar,
            solo_si_primera=False,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Repoblacion completada para la empresa {cuenta_bancaria.empresa}."
            )
        )
        self.stdout.write(f"Pago: {resumen['pago']}")
        self.stdout.write(
            f"CobroOtrosIngresos: {resumen['cobro_otros_ingresos']}"
        )
        self.stdout.write(f"PagoGasto: {resumen['pago_gasto']}")
        self.stdout.write(
            f"FondeoCajaChica: {resumen['fondeo_caja_chica']}"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Total actualizados: {sum(resumen.values())}"
            )
        )