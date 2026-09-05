# ===========================================================
# Y registralo en settings.py, dentro de TEMPLATES -> OPTIONS ->
# context_processors:
#
#     'tu_app.context_processors.notificaciones_sistema_context',
# ============================================================


from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from areas.models import AreaComun
from facturacion.utils import debe_mostrar_recordatorio_facturacion
from notificaciones_sistema.models import NotificacionLeida, NotificacionSistema


def _generar_alertas_automaticas(request):
    """Alertas que GESAC calcula solo, sin que nadie las escriba -- no
    se guardan en base de datos, se recalculan cada vez y desaparecen
    solas cuando ya no aplican."""
    alertas = []
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil:
        return alertas
 
    # 1. Membresia por vencer / ya vencida -- reutiliza el mismo
    # criterio que ya usa el badge de la pantalla de inicio.
    if perfil.tipo_usuario not in ('demo', 'gratis') and perfil.fecha_vencimiento:
        ahora = timezone.now()
        pronto = ahora + timedelta(days=7)
        if perfil.fecha_vencimiento < ahora:
            alertas.append({
                'titulo': 'Tu membresía venció',
                'mensaje': f'Venció el {perfil.fecha_vencimiento.strftime("%d/%m/%Y")} -- renueva para seguir usando el sistema.Tienes 4 dias de gracia',
                'url': reverse('solicitar_pago_transferencia'),
                'icono': 'exclamation-triangle-fill',
                'color': '#9C2B2B',
            })
        elif perfil.fecha_vencimiento <= pronto:
            alertas.append({
                'titulo': 'Tu membresía está por vencer',
                'mensaje': f'Vence el {perfil.fecha_vencimiento.strftime("%d/%m/%Y")} -- renueva a tiempo para no perder el acceso.Tienes 4 dias de gracia',
                'url': reverse('solicitar_pago_transferencia'),
                'icono': 'hourglass-split',
                'color': '#8A6D00',
            })
 
    # 2. Recordatorio de facturacion mensual -- reutiliza la MISMA
    # funcion que ya dispara el modal en la pantalla de inicio.
    empresa = perfil.empresa
    if empresa and debe_mostrar_recordatorio_facturacion(empresa):
        alertas.append({
            'titulo': 'Falta la facturación mensual',
            'mensaje': 'Recuerda generar la facturación de cuotas dentro de los primeros 5 días del mes.',
            'url': reverse('facturar_mes'),
            'icono': 'calendar-check',
            'color': '#8A6D00',
        })

    # 3. NUEVO -- Contratos de areas comunes vencidos o por vencer
    # (30/60/90 dias) -- se agrupan por urgencia en vez de una alerta
    # por cada area, para no saturar la campanita si hay varias.
    if empresa:
        hoy = timezone.now().date()
        areas_activas = AreaComun.objects.filter(empresa=empresa, activo=True, fecha_fin__isnull=False)

        areas_vencidas = areas_activas.filter(fecha_fin__lt=hoy).count()
        areas_30 = areas_activas.filter(fecha_fin__gte=hoy, fecha_fin__lte=hoy + timedelta(days=30)).count()
        areas_60 = areas_activas.filter(
            fecha_fin__gt=hoy + timedelta(days=30), fecha_fin__lte=hoy + timedelta(days=60)
        ).count()
        areas_90 = areas_activas.filter(
            fecha_fin__gt=hoy + timedelta(days=60), fecha_fin__lte=hoy + timedelta(days=90)
        ).count()

        if areas_vencidas:
            alertas.append({
                'titulo': f'{areas_vencidas} contrato(s) de área vencido(s)',
                'mensaje': 'Revisa si renuevan, desocupan, o hay que actualizar su estatus.',
                'url': reverse('lista_areas') + '?vencimiento=vencido',
                'icono': 'exclamation-triangle-fill',
                'color': '#9C2B2B',
            })
        if areas_30:
            alertas.append({
                'titulo': f'{areas_30} contrato(s) vence(n) en 30 días',
                'mensaje': 'Da seguimiento a tiempo para renovación o búsqueda de nuevo arrendatario.',
                'url': reverse('lista_areas') + '?vencimiento=30',
                'icono': 'hourglass-split',
                'color': '#9C2B2B',
            })
        if areas_60:
            alertas.append({
                'titulo': f'{areas_60} contrato(s) vence(n) en 60 días',
                'mensaje': 'Empieza a planear la renovación o búsqueda de nuevo arrendatario.',
                'url': reverse('lista_areas') + '?vencimiento=60',
                'icono': 'hourglass-split',
                'color': '#8A6D00',
            })
        if areas_90:
            alertas.append({
                'titulo': f'{areas_90} contrato(s) vence(n) en 90 días',
                'mensaje': 'Aún tienes tiempo, pero vale la pena tenerlos en el radar.',
                'url': reverse('lista_areas') + '?vencimiento=90',
                'icono': 'calendar3',
                'color': '#8A6D00',
            })    
 
    return alertas


def notificaciones_sistema_context(request):
    if not request.user.is_authenticated:
        return {}
    
    alertas_automaticas = _generar_alertas_automaticas(request)

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

    no_leidas_count = sum(1 for n in activas if not n.leida)+ len(alertas_automaticas)

    return {
        'notif_sistema_count': no_leidas_count,
        'notif_sistema_recientes': activas,
        'alertas_automaticas': alertas_automaticas,
    }