from datetime import date

from django.core.management.base import BaseCommand, CommandError

from leasing.models import Contrato
from leasing.services.calendario import generar_calendario


class Command(BaseCommand):
    help = "Genera/actualiza el calendario de rentas esperadas de un contrato (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int, required=True, help="ID de la empresa")
        parser.add_argument("--contrato", required=True, help="Folio del contrato")
        parser.add_argument("--hasta", required=True, help="Fecha límite YYYY-MM-DD")
        parser.add_argument("--dry-run", action="store_true", help="Calcula y muestra, sin guardar")

    def handle(self, *a, **o):
        try:
            contrato = Contrato.objects.get(empresa_id=o["empresa"], folio=o["contrato"])
        except Contrato.DoesNotExist as e:
            raise CommandError("Contrato no encontrado en esa empresa.") from e
        version = contrato.versiones.filter(es_vigente=True).first()
        if not version:
            raise CommandError("El contrato no tiene versión vigente.")
        hasta = date.fromisoformat(o["hasta"])
        for t in version.terminos.select_related("version__contrato", "empresa"):
            r = generar_calendario(t, hasta, dry_run=o["dry_run"])
            self.stdout.write(str(r))
            for p in r.pendientes:
                self.stdout.write(self.style.WARNING("  PENDIENTE: " + p))
