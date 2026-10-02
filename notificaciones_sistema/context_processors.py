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
from escuelas.models import CarteraVencida
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
 
    
    empresa = perfil.empresa
     # NUEVO -- de aqui en adelante, las alertas se ramifican segun el
    # segmento -- escuela tiene sus propios avisos (nada de GESAC le
    # aplica), y GESAC sigue exactamente igual que antes.
    if empresa and empresa.segmento == 'escuela':
        hoy = timezone.now().date()
 
        # NUEVO -- recordatorio: bajar el reporte de Deudores de
        # Academic+ a partir del dia 11 de cada mes (cuando vencen
        # colegiaturas, talleres, transporte, etc.), si todavia no se
        # ha importado este mes.
        if hoy.day >= 11:
            ya_importo_este_mes = CarteraVencida.objects.filter(
                empresa=empresa,
                fecha_importacion__year=hoy.year,
                fecha_importacion__month=hoy.month,
            ).exists()
            if not ya_importo_este_mes:
                alertas.append({
                    'titulo': 'Actualiza tu Cartera Vencida',
                    'mensaje': 'Ya pasó el día 11 -- baja el reporte de Deudores de Academic+ e impórtalo para tener tus números al día.',
                    'url': reverse('importar_cartera_vencida'),
                    'icono': 'exclamation-triangle-fill',
                    'color': '#8A6D00',
                })
 
        return alertas
 
    # -- A partir de aqui, todo es especifico de GESAC (condominios /
    # plazas) -- nunca se evalua para escuela. --
    # 2. Recordatorio de facturacion mensual -- reutiliza la MISMA
    # funcion que ya dispara el modal en la pantalla de inicio.
    if empresa and debe_mostrar_recordatorio_facturacion(empresa):
        alertas.append({
            'titulo': 'Falta la facturación mensual',
            'mensaje': 'Recuerda generar la facturación de cuotas dentro de los primeros 5 días del mes.',
            'url': reverse('facturar_mes'),
            'icono': 'calendar-check',
            'color': '#8A6D00',
        })

 
    # NUEVO -- "vencido" ahora se basa en el ESTATUS real del contrato
    # (vencido_ocupado), no en fecha_fin directo -- porque el cron de
    # extension mensual mueve fecha_fin hacia adelante cada mes, asi
    # que con el criterio viejo esas areas dejaban de aparecer como
    # vencidas en cuanto se procesaban. Los rangos 30/60/90 si siguen
    # usando fecha_fin, pero solo sobre contratos VIGENTES (su fecha
    # todavia es la fecha real pactada, no una extendida por el cron).
    if empresa:
        hoy = timezone.now().date()
        areas_activas = AreaComun.objects.filter(empresa=empresa, activo=True)

        areas_vencidas = areas_activas.filter(
            contratos__estatus='vencido_ocupado'
        ).distinct().count()

        areas_vigentes_con_fecha = areas_activas.filter(
            contratos__estatus='vigente', fecha_fin__isnull=False
        ).distinct()

        areas_30 = areas_vigentes_con_fecha.filter(
            fecha_fin__gte=hoy, fecha_fin__lte=hoy + timedelta(days=30)
        ).count()
        areas_60 = areas_vigentes_con_fecha.filter(
            fecha_fin__gt=hoy + timedelta(days=30), fecha_fin__lte=hoy + timedelta(days=60)
        ).count()
        areas_90 = areas_vigentes_con_fecha.filter(
            fecha_fin__gt=hoy + timedelta(days=60), fecha_fin__lte=hoy + timedelta(days=90)
        ).count()

        if areas_vencidas:
            alertas.append({
                'titulo': f'{areas_vencidas} contrato(s) "mes a mes"',
                'mensaje': 'Vencieron sin renovarse -- el sistema los extiende solo, pero conviene decidir si renuevan o desocupan.',
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
    # NUEVO -- filtra los avisos manuales segun el segmento del usuario.
    # Vacio ('') = solo GESAC -- asi, todos los avisos ya existentes
    # (creados antes de que existiera escuela) quedan excluidos de
    # escuela automaticamente, sin tocarlos uno por uno.
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil else None

    # NUEVO -- ya no se excluyen las leidas, se mandan TODAS las activas
    # (hasta 5), marcando cada una con .leida = True/False -- asi el
    # template decide como mostrarla (negritas o normal) sin que
    # desaparezca de la lista al leerla.
    activas_qs = NotificacionSistema.objects.filter(activa=True)
    if empresa and empresa.segmento == 'escuela':
        activas_qs = activas_qs.filter(segmento_objetivo__in=['escuela', 'todos'])
    else:
        activas_qs = activas_qs.filter(segmento_objetivo__in=['', 'todos'])
 
    activas = list(activas_qs.order_by('-fecha_creacion')[:5])
    for n in activas:
        n.leida = n.id in ids_leidas
 
    no_leidas_count = sum(1 for n in activas if not n.leida) + len(alertas_automaticas)
 
    return {
        'notif_sistema_count': no_leidas_count,
        'notif_sistema_recientes': activas,
        'alertas_automaticas': alertas_automaticas,
    }