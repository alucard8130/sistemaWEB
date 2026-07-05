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
                # Excluir rutas que no requieren empresa seleccionada
                rutas_excluidas = [
                    '/logout',
                    '/static',
                    '/media',
                    '/portal/',  # ← portal de acceso externo
                    '/admin/',   # ← admin de Django
                ]
                if not any(request.path.startswith(ruta) for ruta in rutas_excluidas):
                    return redirect('seleccionar_empresa')
        return self.get_response(request)