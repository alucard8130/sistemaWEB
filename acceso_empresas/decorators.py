def login_o_portal_required(view_func):
    def wrapper(request, *args, **kwargs):
        # Usuario Django autenticado
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        # Usuario del portal de acceso externo
        if getattr(request, 'is_portal_acceso', False):
            return view_func(request, *args, **kwargs)
        # Verificar sesión del portal directamente
        ua_id = request.session.get('ua_id')
        if ua_id:
            try:
                from acceso_empresas.models import UsuarioAcceso
                ua = UsuarioAcceso.objects.get(pk=ua_id, activo=True)
                request.ua = ua
                return view_func(request, *args, **kwargs)
            except Exception:
                pass
        from django.shortcuts import redirect
        return redirect('login')
    wrapper.__name__ = view_func.__name__
    return wrapper