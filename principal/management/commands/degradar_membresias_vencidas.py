
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from principal.models import PerfilUsuario

# ============================================================
# Colocalo en: cualquier_app/management/commands/degradar_membresias_vencidas.py
#
# Uso (corre esto diario, via cron o el scheduler que ya uses):
#   python manage.py degradar_membresias_vencidas
#
# Degrada a "demo" cualquier PerfilUsuario cuya fecha_vencimiento ya
# paso hace mas de DIAS_GRACIA dias -- sin importar si esa membresia
# se pago por Stripe o por transferencia, ambos usan el mismo campo
# fecha_vencimiento.
# ============================================================


DIAS_GRACIA = 5


class Command(BaseCommand):
    help = (
        f"Degrada a 'demo' cualquier PerfilUsuario cuya membresia vencio "
        f"hace mas de {DIAS_GRACIA} dias sin renovarse."
    )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=DIAS_GRACIA)

        # Nunca se toca 'demo' (ya esta ahi) ni 'gratis' (nivel permanente,
        # no depende de fecha_vencimiento). Tampoco se toca a nadie sin
        # fecha_vencimiento capturada -- eso normalmente significa que
        # nunca se le dio seguimiento de vencimiento a proposito.
        perfiles_a_degradar = (
            PerfilUsuario.objects.filter(fecha_vencimiento__lt=limite)
            .exclude(tipo_usuario__in=['demo', 'gratis'])
            .exclude(fecha_vencimiento__isnull=True)
        )

        total = perfiles_a_degradar.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No hay membresias que degradar hoy."))
            return

        for perfil in perfiles_a_degradar:
            tipo_anterior = perfil.get_tipo_usuario_display()
            perfil.tipo_usuario = 'demo'
            perfil.save(update_fields=['tipo_usuario'])
            self.stdout.write(
                f"  {perfil.usuario.username} ({perfil.empresa.nombre if perfil.empresa else 'sin empresa'}) "
                f"-- {tipo_anterior} -> Demo (vencio: {perfil.fecha_vencimiento:%d/%m/%Y})"
            )

        self.stdout.write(self.style.SUCCESS(f"\n{total} perfil(es) degradado(s) a Demo."))