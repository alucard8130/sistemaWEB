
def empresa_actual(request):
    """Expone la empresa del usuario actual (o la seleccionada en sesión si
    es superusuario) en TODOS los templates, sin que cada vista tenga que
    pasarla explícitamente. Útil para adaptar menús/etiquetas por segmento."""
    if not request.user.is_authenticated:
        return {}

    empresa = None
    if request.user.is_superuser:
        empresa_id = request.session.get('empresa_id')
        if empresa_id:
            from empresas.models import Empresa
            empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        perfil = getattr(request.user, 'perfilusuario', None)
        empresa = perfil.empresa if perfil else None

    return {'empresa_actual': empresa}