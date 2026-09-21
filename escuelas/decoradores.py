from functools import wraps

from django.shortcuts import redirect
from django.utils import timezone


def requiere_membresia_activa_escuela(view_func):
    """Bloquea el acceso si el usuario es de una escuela y:
    - su demo ya lleva mas de 10 dias (desde que se registro), o
    - su membresia Plus ya vencio y no la ha renovado.
    Para usuarios que NO son de escuela, no hace nada -- pasa de largo."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        perfil = getattr(request.user, 'perfilusuario', None)
        if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
            return view_func(request, *args, **kwargs)

        if perfil.tipo_usuario == 'demo':
            dias_transcurridos = (timezone.now().date() - request.user.date_joined.date()).days
            if dias_transcurridos > 10:
                return redirect('membresia_vencida_escuela')
        elif perfil.fecha_vencimiento and perfil.fecha_vencimiento < timezone.now():
            return redirect('membresia_vencida_escuela')

        return view_func(request, *args, **kwargs)

    return wrapper