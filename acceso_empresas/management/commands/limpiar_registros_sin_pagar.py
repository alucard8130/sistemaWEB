# Crea el archivo:
# acceso_empresas/management/commands/limpiar_registros_sin_pagar.py
# (con __init__.py vacios en management/ y management/commands/ si no
# existen)

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from acceso_empresas.models import UsuarioAcceso


class Command(BaseCommand):
    help = "Borra cuentas del Portal de Acceso que nunca completaron el pago, despues de 24 horas."
 
    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=24)
 
        candidatos = UsuarioAcceso.objects.filter(
            activo=False,
            fecha_registro__lt=limite,
        ).filter(
            Q(stripe_subscription_id__isnull=True) | Q(stripe_subscription_id=''),
        )
 
        total = candidatos.count()
        candidatos.delete()
 
        self.stdout.write(self.style.SUCCESS(
            f"{total} cuenta(s) sin pagar eliminada(s) (mas de 24 horas sin completar el pago)."
        ))
