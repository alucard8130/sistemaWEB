from django.shortcuts import redirect
from django.urls import reverse

class EmpresaSeleccionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_superuser:
            if not request.session.get('empresa_id') and \
               request.path != reverse('seleccionar_empresa'):
                rutas_excluidas = ['/logout', '/static', '/media', '/portal/', '/admin/']
                if not any(request.path.startswith(r) for r in rutas_excluidas):
                    return redirect('seleccionar_empresa')
        return self.get_response(request)