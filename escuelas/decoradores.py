from functools import wraps

from django.shortcuts import redirect
from django.utils import timezone

from core.gracia import limite_gracia


def empresa_activa(request):
    """Empresa con la que se esta trabajando: para el superusuario, la que
    eligio en el selector del menu (sesion); para los demas, la de su perfil."""
    user = request.user
    if user.is_superuser:
        empresa_id = request.session.get('empresa_id')
        if empresa_id:
            from empresas.models import Empresa
            empresa = Empresa.objects.filter(id=empresa_id).first()
            if empresa:
                return empresa
    perfil = getattr(user, 'perfilusuario', None)
    return perfil.empresa if perfil else None


def requiere_membresia_activa_escuela(view_func):
    """Bloquea el acceso si el usuario es de una escuela y:
    - su demo ya lleva mas de 10 dias (desde que se registro), o
    - su membresia Plus ya vencio y paso el plazo de gracia (dia 15 del mes).
    Para usuarios que NO son de escuela, no hace nada -- pasa de largo."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # El superusuario no esta sujeto a la membresia de la escuela.
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        perfil = getattr(request.user, 'perfilusuario', None)
        if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
            return view_func(request, *args, **kwargs)

        if perfil.tipo_usuario == 'demo':
            dias_transcurridos = (timezone.now().date() - request.user.date_joined.date()).days
            if dias_transcurridos > 10:
                return redirect('membresia_vencida_escuela')
        elif perfil.fecha_vencimiento and timezone.now() > limite_gracia(perfil.fecha_vencimiento, escuela=True):
            # Gracia hasta el dia 15 del mes en que vencio (ver core/gracia.py).
            return redirect('membresia_vencida_escuela')

        return view_func(request, *args, **kwargs)

    return wrapper