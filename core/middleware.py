from datetime import timedelta

from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone


class EmpresaSeleccionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_superuser:  # noqa: SIM102
            if not request.session.get('empresa_id') and \
               request.path != reverse('seleccionar_empresa'):
                rutas_excluidas = ['/logout', '/static', '/media', '/portal/', '/admin/']
                if not any(request.path.startswith(r) for r in rutas_excluidas):
                    return redirect('seleccionar_empresa')
        return self.get_response(request)



#middleware de bloqueo de membresía#############

DIAS_GRACIA_BLOQUEO = 2

# Nombres de URL que SIEMPRE deben quedar accesibles aunque la cuenta
# este bloqueada -- si falta alguno aqui, el usuario queda atrapado
# sin poder ni pagar ni salir. Ajusta estos nombres a los reales de
# tu urls.py.
URLS_PERMITIDAS_BLOQUEADO = {
    'login', 'logout', 'cuenta_bloqueada',
    'solicitar_pago_transferencia', 'crear_sesion_pago', 'crear_sesion_pago_premium',
    'stripe_webhook',
    'password_reset', 'password_reset_done', 'password_reset_confirm', 'password_reset_complete',
}


class MembresiaBloqueoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._debe_bloquear(request):
            return redirect('cuenta_bloqueada')
        return self.get_response(request)

    def _debe_bloquear(self, request):
        if not request.user.is_authenticated or request.user.is_superuser:
            return False

        if request.path.startswith(settings.STATIC_URL) or (
            getattr(settings, 'MEDIA_URL', None) and request.path.startswith(settings.MEDIA_URL)
        ):
            return False

        try:
            url_name = resolve(request.path).url_name
        except Resolver404:
            url_name = None

        if url_name in URLS_PERMITIDAS_BLOQUEADO:
            return False

        perfil = getattr(request.user, 'perfilusuario', None)
        if not perfil:
            return False

        if perfil.tipo_usuario in ('demo', 'gratis'):
            return False

        if not perfil.fecha_vencimiento:
            return False

        limite_bloqueo = timezone.now() - timedelta(days=DIAS_GRACIA_BLOQUEO)
        return perfil.fecha_vencimiento < limite_bloqueo    