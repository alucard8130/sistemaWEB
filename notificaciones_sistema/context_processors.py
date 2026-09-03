# ===========================================================
# Y registralo en settings.py, dentro de TEMPLATES -> OPTIONS ->
# context_processors:
#
#     'tu_app.context_processors.notificaciones_sistema_context',
# ============================================================


from notificaciones_sistema.models import NotificacionLeida, NotificacionSistema


def notificaciones_sistema_context(request):
    if not request.user.is_authenticated:
        return {}

    ids_leidas = set(
        NotificacionLeida.objects.filter(usuario=request.user)
        .values_list('notificacion_id', flat=True)
    )

    # NUEVO -- ya no se excluyen las leidas, se mandan TODAS las activas
    # (hasta 5), marcando cada una con .leida = True/False -- asi el
    # template decide como mostrarla (negritas o normal) sin que
    # desaparezca de la lista al leerla.
    activas = list(NotificacionSistema.objects.filter(activa=True).order_by('-fecha_creacion')[:5])
    for n in activas:
        n.leida = n.id in ids_leidas

    no_leidas_count = sum(1 for n in activas if not n.leida)

    return {
        'notif_sistema_count': no_leidas_count,
        'notif_sistema_recientes': activas,
    }