# ============================================================
#
# Y registralo en settings.py, dentro de TEMPLATES -> OPTIONS ->
# context_processors (agrega esta linea a la lista que ya tienes):
#
#     'acceso_empresas.context_processors.alertas_portal_context',
#
# Con esto, TODAS las plantillas del portal (cualquiera que use
# este navbar) tienen acceso a "alertas_no_leidas_count" y
# "alertas_recientes" automaticamente, sin que cada vista tenga
# que pasarlas a mano.
# ============================================================

from acceso_empresas.models import AlertaGesac  # ajusta el import a tu ruta real


def alertas_portal_context(request):
    ua_id = request.session.get('ua_id')
    if not ua_id:
        return {}

    alertas_no_leidas_qs = AlertaGesac.objects.filter(
        usuario_acceso_id=ua_id, leida=False
    ).select_related('empresa').order_by('-fecha_creacion')

    return {
        'alertas_no_leidas_count': alertas_no_leidas_qs.count(),
        'alertas_recientes': alertas_no_leidas_qs[:8],
    }