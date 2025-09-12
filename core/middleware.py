from django.shortcuts import redirect
from django.urls import reverse

class EmpresaSeleccionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo aplica si el usuario está autenticado y es superusuario
        if request.user.is_authenticated and request.user.is_superuser:
            # Si no está en la vista de seleccionar empresa y no tiene empresa en sesión
            if not request.session.get('empresa_id') and request.path != reverse('seleccionar_empresa'):
                # Evita redirigir en logout/login/static/media
                if not request.path.startswith('/logout') and not request.path.startswith('/static') and not request.path.startswith('/media'):
                    return redirect('seleccionar_empresa')
        return self.get_response(request)