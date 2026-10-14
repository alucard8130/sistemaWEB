"""Acceso al módulo: login + empresa del segmento 'arrendamiento' + permiso de Django."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from empresas.models import Empresa


def empresa_de(request):
    """Misma regla que ``empresas.context_processors.empresa_actual``.

    Un superusuario usa la empresa de su sesión; si no tiene y solo existe UNA empresa
    de arrendamiento, usa esa.
    """
    u = request.user
    if u.is_superuser:
        eid = request.session.get("empresa_id")
        if eid:
            return Empresa.objects.filter(pk=eid).first()
        unicas = list(Empresa.objects.filter(segmento="arrendamiento")[:2])
        return unicas[0] if len(unicas) == 1 else None
    perfil = getattr(u, "perfilusuario", None)
    return perfil.empresa if perfil else None


def leasing_view(perm="leasing.view_contrato"):
    def deco(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            empresa = empresa_de(request)
            if empresa is None or empresa.segmento != "arrendamiento":
                messages.warning(
                    request, "Este módulo solo está disponible para empresas del segmento Arrendamiento."
                )
                return redirect("dashboard_inicio")
            if not request.user.has_perm(perm):
                raise PermissionDenied
            request.empresa_leasing = empresa
            return fn(request, *args, **kwargs)

        return login_required(wrapper)

    return deco
