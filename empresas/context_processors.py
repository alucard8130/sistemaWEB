# Etiquetas de los grupos del selector de empresa del superusuario.
_TITULOS_SEGMENTO = {
    'comercial': 'Comercial (plazas)',
    'habitacional': 'Habitacional (condominios)',
    'escuela': 'Campus (escuelas)',
    'arrendamiento': 'Leasing (arrendamiento)',
}


def empresa_actual(request):
    """Expone la empresa del usuario actual (o la seleccionada en sesión si
    es superusuario) en TODOS los templates, sin que cada vista tenga que
    pasarla explícitamente. Útil para adaptar menús/etiquetas por segmento.

    Para el superusuario expone además 'grupos_empresas' (todas las
    empresas agrupadas por segmento) para el selector de empresa del menú."""
    if not request.user.is_authenticated:
        return {}

    empresa = None
    contexto = {}
    if request.user.is_superuser:
        from empresas.models import Empresa
        empresa_id = request.session.get('empresa_id')
        if empresa_id:
            empresa = Empresa.objects.filter(id=empresa_id).first()
        if empresa is None:
            # Respaldo: la empresa de su propio perfil (el middleware
            # EmpresaSuperusuarioMiddleware normalmente ya dejó una en sesión).
            perfil = getattr(request.user, 'perfilusuario', None)
            empresa = perfil.empresa if perfil else None

        grupos = {}
        for e in Empresa.objects.order_by('nombre').values('id', 'nombre', 'segmento'):
            grupos.setdefault(e['segmento'], []).append(e)
        contexto['grupos_empresas'] = [
            {'titulo': _TITULOS_SEGMENTO.get(seg, seg.title()), 'empresas': grupos[seg]}
            for seg in _TITULOS_SEGMENTO if seg in grupos
        ] + [
            {'titulo': seg.title(), 'empresas': lista}
            for seg, lista in grupos.items() if seg not in _TITULOS_SEGMENTO
        ]
    else:
        perfil = getattr(request.user, 'perfilusuario', None)
        empresa = perfil.empresa if perfil else None

    contexto['empresa_actual'] = empresa
    return contexto
