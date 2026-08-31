
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from principal.models import PerfilUsuario

# Degrada a "demo" cualquier PerfilUsuario cuya fecha_vencimiento ya
# paso hace mas de DIAS_ANTES_DEGRADAR dias -- sin importar si esa
# membresia se pago por Stripe o por transferencia, ambos usan el
# mismo campo fecha_vencimiento.
#
# NOTA -- este es el SEGUNDO paso del ciclo de vencimiento. El primer
# paso (bloqueo total de acceso a los 5 dias) lo hace
# MembresiaBloqueoMiddleware, no este comando -- este solo se encarga
# de la degradacion final si sigue sin renovar despues de eso.



# 5 dias de gracia antes del bloqueo (ver middleware.py) + 15 dias
# adicionales bloqueado sin renovar = 20 dias totales desde que vencio.
DIAS_ANTES_DEGRADAR = 20
 
 
class Command(BaseCommand):
    help = (
        f"Degrada a 'demo' cualquier PerfilUsuario cuya membresia vencio "
        f"hace mas de {DIAS_ANTES_DEGRADAR} dias sin renovarse."
    )
 
    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=DIAS_ANTES_DEGRADAR)
 
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
 
            # NUEVO -- degrada también la empresa en AMBOS campos (plus y
            # premium), verificando primero que NINGÚN otro PerfilUsuario
            # de esa misma empresa siga vigente (ej. dueño + co-administrador,
            # cada uno con su propio perfil).
            if perfil.empresa and (perfil.empresa.es_plus or perfil.empresa.es_premium):
                otros_perfiles_vigentes = (
                    PerfilUsuario.objects.filter(empresa=perfil.empresa)
                    .exclude(id=perfil.id)
                    .exclude(tipo_usuario__in=['demo', 'gratis'])
                    .filter(fecha_vencimiento__gte=limite)
                )
                if not otros_perfiles_vigentes.exists():
                    perfil.empresa.es_plus = False
                    perfil.empresa.es_premium = False
                    perfil.empresa.save(update_fields=['es_plus', 'es_premium'])
 
            self.stdout.write(
                f"  {perfil.usuario.username} ({perfil.empresa.nombre if perfil.empresa else 'sin empresa'}) "
                f"-- {tipo_anterior} -> Demo (vencio: {perfil.fecha_vencimiento:%d/%m/%Y})"
            )
 
        self.stdout.write(self.style.SUCCESS(f"\n{total} perfil(es) degradado(s) a Demo."))