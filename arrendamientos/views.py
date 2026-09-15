import calendar
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import requests
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from areas.models import AreaComun

# AJUSTA este import a donde realmente viva generar_facturas_area en tu proyecto:
from areas.utility import generar_facturas_area
from clientes.models import Cliente
from core import settings

from .models import ContratoArea, ReporteVentasContrato


# ============================================================
# Historial de contratos por área
# ============================================================
@login_required
def historial_contratos_area(request, area_id):
    area = get_object_or_404(AreaComun, id=area_id)
    contratos = area.contratos.all()
    return render(request, 'arrendamientos/historial_contratos.html', {
        'area': area,
        'contratos': contratos,
    })


# ============================================================
# Crear / renovar contrato (manual, vía formulario)
# ============================================================
@login_required
def crear_contrato_area(request, area_id):
    area = get_object_or_404(AreaComun, id=area_id)
    contrato_vigente = area.contratos.filter(estatus__in=['vigente', 'vencido_ocupado']).first()

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        cuota_str = request.POST.get('cuota', '').strip()
        deposito_str = request.POST.get('deposito', '').strip()
        fecha_firma_str = request.POST.get('fecha_firma', '').strip()
        fecha_inicio_str = request.POST.get('fecha_inicio', '').strip()
        fecha_fin_str = request.POST.get('fecha_fin', '').strip()
        plazo_forzoso_str = request.POST.get('plazo_forzoso_meses', '').strip()
        renovacion_automatica = request.POST.get('renovacion_automatica') == 'on'
        tipo_incremento = request.POST.get('tipo_incremento', 'ninguno')
        porcentaje_incremento_str = request.POST.get('porcentaje_incremento', '').strip()
        periodicidad_facturacion = request.POST.get('periodicidad_facturacion', 'mensual')
        tipo_renta = request.POST.get('tipo_renta', 'fija')
        porcentaje_ventas_str = request.POST.get('porcentaje_ventas', '').strip()
        incluye_mantenimiento = request.POST.get('incluye_mantenimiento') == 'on'
        cuota_mantenimiento_str = request.POST.get('cuota_mantenimiento', '').strip()
        penalizacion_str = request.POST.get('penalizacion_atraso_porcentaje', '').strip()
        clausulas_especiales = request.POST.get('clausulas_especiales', '').strip()
        contrato_pdf = request.FILES.get('contrato_pdf')

        if not cliente_id or not fecha_firma_str or not fecha_inicio_str or not cuota_str:
            messages.error(request, "Cliente, fecha de firma, fecha de inicio, y cuota son obligatorios.")
            return redirect('crear_contrato_area', area_id=area_id)

        try:
            fecha_firma = datetime.strptime(fecha_firma_str, '%Y-%m-%d').date()  # noqa: DTZ007
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()  # noqa: DTZ007
        except ValueError:
            messages.error(request, "Las fechas capturadas no son válidas.")
            return redirect('crear_contrato_area', area_id=area_id)

        if fecha_firma > fecha_inicio:
            messages.error(request, "La fecha de firma no puede ser posterior a la fecha de inicio.")
            return redirect('crear_contrato_area', area_id=area_id)

        
        # ---- Plazo forzoso y fecha_fin, mutuamente calculables --
        # fecha_fin SIEMPRE cae en el ultimo dia de un mes, sin importar
        # que dia del mes haya iniciado el contrato (mismo criterio que
        # usamos para el vencimiento de membresias).
        plazo_forzoso_meses = None
        if plazo_forzoso_str:
            try:
                plazo_forzoso_meses = int(plazo_forzoso_str)
            except ValueError:
                messages.error(request, "El plazo forzoso capturado no es válido.")
                return redirect('crear_contrato_area', area_id=area_id)

        fecha_fin = None
        if fecha_fin_str:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()  # noqa: DTZ007
            except ValueError:
                messages.error(request, "La fecha fin capturada no es válida.")
                return redirect('crear_contrato_area', area_id=area_id)

        if not plazo_forzoso_meses and not fecha_fin:
            messages.error(request, "Captura el plazo forzoso en meses, o la fecha de fin del contrato.")
            return redirect('crear_contrato_area', area_id=area_id)

        def _fin_de_mes(fecha_base, meses_a_sumar):
            mes_objetivo = fecha_base + relativedelta(months=meses_a_sumar - 1)
            ultimo_dia = calendar.monthrange(mes_objetivo.year, mes_objetivo.month)[1]
            return date(mes_objetivo.year, mes_objetivo.month, ultimo_dia)

        if plazo_forzoso_meses and not fecha_fin:
            fecha_fin = _fin_de_mes(fecha_inicio, plazo_forzoso_meses)
        elif fecha_fin and not plazo_forzoso_meses:
            delta = relativedelta(fecha_fin, fecha_inicio)
            plazo_forzoso_meses = delta.years * 12 + delta.months
            if delta.days > 0:
                plazo_forzoso_meses += 1
        else:
            fecha_fin_calculada = _fin_de_mes(fecha_inicio, plazo_forzoso_meses)
            if abs((fecha_fin - fecha_fin_calculada).days) > 3:
                messages.error(
                    request,
                    f"El plazo forzoso ({plazo_forzoso_meses} meses) no coincide con las fechas "
                    f"capturadas -- según las fechas, la fecha fin debería ser aproximadamente "
                    f"{fecha_fin_calculada.strftime('%d/%m/%Y')}."
                )
                return redirect('crear_contrato_area', area_id=area_id)

        if fecha_fin <= fecha_inicio:
            messages.error(request, "La fecha de fin debe ser posterior a la fecha de inicio.")
            return redirect('crear_contrato_area', area_id=area_id)

        # ---- Montos ----
        try:
            cuota = Decimal(cuota_str)
        except (InvalidOperation, TypeError):
            messages.error(request, "La cuota capturada no es válida.")
            return redirect('crear_contrato_area', area_id=area_id)

        deposito = None
        if deposito_str:
            try:
                deposito = Decimal(deposito_str)
            except (InvalidOperation, TypeError):
                messages.error(request, "El depósito capturado no es válido.")
                return redirect('crear_contrato_area', area_id=area_id)

        porcentaje_incremento = None
        if tipo_incremento == 'porcentaje_fijo':
            if not porcentaje_incremento_str:
                messages.error(request, "Captura el % de incremento pactado.")
                return redirect('crear_contrato_area', area_id=area_id)
            try:
                porcentaje_incremento = Decimal(porcentaje_incremento_str)
            except (InvalidOperation, TypeError):
                messages.error(request, "El % de incremento capturado no es válido.")
                return redirect('crear_contrato_area', area_id=area_id)

        porcentaje_ventas = None
        if tipo_renta in ('variable', 'mixta'):
            if not porcentaje_ventas_str:
                messages.error(request, "Captura el % sobre ventas para renta variable o mixta.")
                return redirect('crear_contrato_area', area_id=area_id)
            try:
                porcentaje_ventas = Decimal(porcentaje_ventas_str)
            except (InvalidOperation, TypeError):
                messages.error(request, "El % sobre ventas capturado no es válido.")
                return redirect('crear_contrato_area', area_id=area_id)

        cuota_mantenimiento = None
        if incluye_mantenimiento:
            if not cuota_mantenimiento_str:
                messages.error(request, "Captura el monto de la cuota de mantenimiento.")
                return redirect('crear_contrato_area', area_id=area_id)
            try:
                cuota_mantenimiento = Decimal(cuota_mantenimiento_str)
            except (InvalidOperation, TypeError):
                messages.error(request, "La cuota de mantenimiento capturada no es válida.")
                return redirect('crear_contrato_area', area_id=area_id)

        penalizacion_atraso_porcentaje = None
        if penalizacion_str:
            try:
                penalizacion_atraso_porcentaje = Decimal(penalizacion_str)
            except (InvalidOperation, TypeError):
                messages.error(request, "La penalización capturada no es válida.")
                return redirect('crear_contrato_area', area_id=area_id)

        # NUEVO -- valida que las fechas del contrato nuevo no se empalmen
        # con NINGUN otro contrato de esta misma area (pasado, presente, o
        # futuro) -- un area fisica no puede tener 2 arrendatarios al mismo
        # tiempo, ni siquiera en periodos historicos. Se excluye el contrato
        # que se esta renovando (si aplica), ya que su fin y el inicio del
        # nuevo son contiguos por diseno.
        contratos_a_verificar = area.contratos.all()
        if contrato_vigente:
            contratos_a_verificar = contratos_a_verificar.exclude(pk=contrato_vigente.pk)

        contrato_empalmado = contratos_a_verificar.filter(
            fecha_inicio__lte=fecha_fin, fecha_fin__gte=fecha_inicio
        ).first()

        if contrato_empalmado:
            messages.error(
                request,
                f"Las fechas capturadas ({fecha_inicio.strftime('%d/%m/%Y')} a "
                f"{fecha_fin.strftime('%d/%m/%Y')}) se empalman con otro contrato de esta área -- "
                f"{contrato_empalmado.cliente.nombre} "
                f"({contrato_empalmado.fecha_inicio.strftime('%d/%m/%Y')} a "
                f"{contrato_empalmado.fecha_fin.strftime('%d/%m/%Y')}, "
                f"estatus: {contrato_empalmado.get_estatus_display()}). Ajusta las fechas."
            )
            return redirect('crear_contrato_area', area_id=area_id)
        

        cliente = get_object_or_404(Cliente, id=cliente_id)
        giro = request.POST.get('giro', '').strip()

        with transaction.atomic():
            if contrato_vigente:
                contrato_vigente.estatus = 'renovado'
                contrato_vigente.save(update_fields=['estatus'])

            nuevo_contrato = ContratoArea.objects.create(
                area=area,
                cliente=cliente,
                giro=giro or None,
                fecha_firma=fecha_firma,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                cuota=cuota,
                deposito=deposito,
                plazo_forzoso_meses=plazo_forzoso_meses,
                renovacion_automatica=renovacion_automatica,
                tipo_incremento=tipo_incremento,
                porcentaje_incremento=porcentaje_incremento,
                periodicidad_facturacion=periodicidad_facturacion,
                tipo_renta=tipo_renta,
                porcentaje_ventas=porcentaje_ventas,
                incluye_mantenimiento=incluye_mantenimiento,
                cuota_mantenimiento=cuota_mantenimiento,
                penalizacion_atraso_porcentaje=penalizacion_atraso_porcentaje,
                clausulas_especiales=clausulas_especiales or None,
                contrato_pdf=contrato_pdf,
                contrato_anterior=contrato_vigente,
                creado_por=request.user,
            )
            nuevo_contrato.sincronizar_a_area()

        mensaje_base = f"Contrato {'renovado' if contrato_vigente else 'creado'} para el área {area.numero}."
        try:
            generar_facturas_area(area)
            messages.success(request, f"{mensaje_base} Se generó su facturación inicial.")
        except Exception as e:  # noqa: BLE001
            messages.warning(
                request,
                f"{mensaje_base} El contrato se guardó correctamente, pero no se pudo generar "
                f"la facturación inicial ({e}) -- puedes generarla manualmente desde Facturación."
            )

        return redirect('historial_contratos_area', area_id=area.id)

    return render(request, 'arrendamientos/crear_contrato.html', {
        'area': area,
        'contrato_vigente': contrato_vigente,
        'tipo_incremento_choices': ContratoArea.TIPO_INCREMENTO_CHOICES,
        'tipo_renta_choices': ContratoArea.TIPO_RENTA_CHOICES,
        'periodicidad_choices': ContratoArea.PERIODICIDAD_CHOICES,
        'clientes': Cliente.objects.filter(empresa=area.empresa, activo=True).order_by('nombre'),
    })


# ============================================================
# Terminar contrato sin renovar -- libera el área
# ============================================================
@login_required
def terminar_contrato_area(request, contrato_id):
    if request.method != 'POST':
        return redirect('dashboard_inicio')

    contrato = get_object_or_404(ContratoArea, id=contrato_id, estatus__in=['vigente', 'vencido_ocupado'])
    contrato.estatus = 'terminado'
    contrato.save(update_fields=['estatus'])

    area = contrato.area
    area.status = 'disponible'
    area.cliente = None
    area.save(update_fields=['status', 'cliente'])

    messages.success(request, f"Contrato de {area.numero} terminado -- el área quedó disponible.")
    return redirect('historial_contratos_area', area_id=area.id)


# ============================================================
# Gestión de contratos -- vencidos o por vencer (30 días)
# ============================================================
# @login_required
# def gestion_contratos_areas(request):
#     perfil = getattr(request.user, 'perfilusuario', None)
#     if not perfil or not perfil.empresa:
#         messages.error(request, "No tienes una empresa asociada.")
#         return redirect('dashboard_inicio')

#     hoy = date.today()
#     ventana_maxima = hoy + timedelta(days=30)

#     contratos_candidatos = ContratoArea.objects.filter(
#         area__empresa=perfil.empresa, estatus='vigente',
#         fecha_fin__lte=ventana_maxima,
#     ).select_related('area', 'cliente').order_by('fecha_fin')

#     pendientes = []
#     for contrato in contratos_candidatos:
#         dias_para_vencer = (contrato.fecha_fin - hoy).days
#         pendientes.append({
#             'contrato': contrato,
#             'dias_para_vencer': dias_para_vencer,
#             'dias_vencido': abs(dias_para_vencer) if dias_para_vencer < 0 else 0,
#             'vencido': dias_para_vencer < 0,
#         })

#     return render(request, 'arrendamientos/gestion_contratos.html', {'pendientes': pendientes})
@login_required
def gestion_contratos_areas(request):
    """Expediente completo de contratos -- TODOS los contratos de la
    empresa (vigentes, vencidos, renovados, terminados), con busqueda
    y filtro por estatus. Ya no se limita a los que vencen en 30 dias."""
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    q = request.GET.get('q', '').strip()
    filtro_estatus = request.GET.get('estatus', '')
 
    contratos = ContratoArea.objects.filter(
        area__empresa=perfil.empresa
    ).select_related('area', 'cliente').order_by('-fecha_inicio')
 
    if q:
        contratos = contratos.filter(
            Q(area__numero__icontains=q) | Q(cliente__nombre__icontains=q)
        )
 
    # if filtro_estatus == 'vencido':
    #     contratos = [c for c in contratos if c.esta_vencido]
    # elif filtro_estatus:
    #     contratos = contratos.filter(estatus=filtro_estatus)
    if filtro_estatus:
        contratos = contratos.filter(estatus=filtro_estatus)
 
    paginator = Paginator(contratos, 25)
    page_number = request.GET.get('page')
    contratos_pagina = paginator.get_page(page_number)
 
    return render(request, 'arrendamientos/gestion_contratos.html', {
        'contratos': contratos_pagina,
        'q': q,
        'filtro_estatus': filtro_estatus,
    })


# ============================================================
# Renovar con un clic, aplicando el % pactado
# ============================================================
# @login_required
# def renovar_contrato_automatico(request, contrato_id):
#     if request.method != 'POST':
#         return redirect('gestion_contratos_areas')

#     contrato_actual = get_object_or_404(ContratoArea, id=contrato_id, estatus='vigente')

#     if not contrato_actual.renovacion_automatica or contrato_actual.tipo_incremento != 'porcentaje_fijo':
#         messages.error(request, "Este contrato no tiene renovación automática con % pactado configurada.")
#         return redirect('gestion_contratos_areas')

#     area = contrato_actual.area
#     porcentaje = contrato_actual.porcentaje_incremento or Decimal('0')  # noqa: FURB157

#     nueva_fecha_inicio = contrato_actual.fecha_fin + timedelta(days=1)
@login_required
def renovar_contrato_automatico(request, contrato_id):
    if request.method != 'POST':
        return redirect('gestion_contratos_areas')

    contrato_actual = get_object_or_404(ContratoArea, id=contrato_id, estatus='vigente')

    if not contrato_actual.renovacion_automatica or contrato_actual.tipo_incremento not in ('porcentaje_fijo', 'inpc'):
        messages.error(request, "Este contrato no tiene renovación automática configurada.")
        return redirect('gestion_contratos_areas')

    area = contrato_actual.area

    if contrato_actual.tipo_incremento == 'porcentaje_fijo':
        porcentaje = contrato_actual.porcentaje_incremento or Decimal('0')  # noqa: FURB157
    else:
        porcentaje = calcular_incremento_inpc(contrato_actual.fecha_inicio)
        if porcentaje is None:
            messages.error(
                request,
                "No se pudo consultar el INPC en este momento (revisa tu token de Banxico "
                "o tu conexión) -- intenta de nuevo más tarde, o renueva manualmente "
                "capturando el % a mano."
            )
            return redirect('gestion_contratos_areas')

    nueva_fecha_inicio = contrato_actual.fecha_fin + timedelta(days=1)

    plazo = contrato_actual.plazo_forzoso_meses
    if plazo:
        mes_objetivo = nueva_fecha_inicio + relativedelta(months=plazo - 1)
        ultimo_dia = calendar.monthrange(mes_objetivo.year, mes_objetivo.month)[1]
        nueva_fecha_fin = date(mes_objetivo.year, mes_objetivo.month, ultimo_dia)
    else:
        duracion_dias = (contrato_actual.fecha_fin - contrato_actual.fecha_inicio).days
        nueva_fecha_fin_sin_ajustar = nueva_fecha_inicio + timedelta(days=duracion_dias)
        ultimo_dia = calendar.monthrange(nueva_fecha_fin_sin_ajustar.year, nueva_fecha_fin_sin_ajustar.month)[1]
        nueva_fecha_fin = date(nueva_fecha_fin_sin_ajustar.year, nueva_fecha_fin_sin_ajustar.month, ultimo_dia)
        

    factor = Decimal('1') + (porcentaje / Decimal('100'))  # noqa: FURB157
    nueva_cuota = (contrato_actual.cuota * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    with transaction.atomic():
        contrato_actual.estatus = 'renovado'
        contrato_actual.save(update_fields=['estatus'])

        nuevo_contrato = ContratoArea.objects.create(
            area=area,
            cliente=contrato_actual.cliente,
            fecha_firma=nueva_fecha_inicio,
            fecha_inicio=nueva_fecha_inicio,
            fecha_fin=nueva_fecha_fin,
            cuota=nueva_cuota,
            deposito=contrato_actual.deposito,
            plazo_forzoso_meses=plazo,
            renovacion_automatica=contrato_actual.renovacion_automatica,
            tipo_incremento=contrato_actual.tipo_incremento,
            porcentaje_incremento=contrato_actual.porcentaje_incremento,
            periodicidad_facturacion=contrato_actual.periodicidad_facturacion,
            tipo_renta=contrato_actual.tipo_renta,
            porcentaje_ventas=contrato_actual.porcentaje_ventas,
            incluye_mantenimiento=contrato_actual.incluye_mantenimiento,
            cuota_mantenimiento=contrato_actual.cuota_mantenimiento,
            penalizacion_atraso_porcentaje=contrato_actual.penalizacion_atraso_porcentaje,
            estatus_deposito=contrato_actual.estatus_deposito,
            clausulas_especiales=contrato_actual.clausulas_especiales,
            contrato_anterior=contrato_actual,
            creado_por=request.user,
        )
        nuevo_contrato.sincronizar_a_area()

    mensaje_base = (
        f"Contrato del área {area.numero} renovado automáticamente hasta "
        f"{nueva_fecha_fin.strftime('%d/%m/%Y')} -- nueva renta ${nueva_cuota} ({porcentaje}% de incremento)."
    )
    try:
        generar_facturas_area(area)
        messages.success(request, f"{mensaje_base} Se generó su facturación inicial.")
    except Exception as e:  # noqa: BLE001
        messages.warning(
            request,
            f"{mensaje_base} El contrato se guardó correctamente, pero no se pudo generar "
            f"la facturación inicial ({e})."
        )

    return redirect('gestion_contratos_areas')


# ============================================================
# Captura de ventas -- renta variable o mixta
# ============================================================
@login_required
def capturar_ventas_contrato(request, contrato_id):
    contrato = get_object_or_404(ContratoArea, id=contrato_id, estatus__in=['vigente', 'vencido_ocupado'])

    if contrato.tipo_renta == 'fija':
        messages.error(request, "Este contrato tiene renta fija -- no requiere captura de ventas.")
        return redirect('historial_contratos_area', area_id=contrato.area.id)

    if request.method == 'POST':
        periodo_inicio_str = request.POST.get('periodo_inicio', '').strip()
        periodo_fin_str = request.POST.get('periodo_fin', '').strip()
        monto_ventas_str = request.POST.get('monto_ventas', '').strip()

        if not periodo_inicio_str or not periodo_fin_str or not monto_ventas_str:
            messages.error(request, "El periodo y el monto de ventas son obligatorios.")
            return redirect('capturar_ventas_contrato', contrato_id=contrato_id)

        try:
            periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()  # noqa: DTZ007
            periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()  # noqa: DTZ007
        except ValueError:
            messages.error(request, "Las fechas del periodo no son válidas.")
            return redirect('capturar_ventas_contrato', contrato_id=contrato_id)

        if periodo_fin <= periodo_inicio:
            messages.error(request, "El fin del periodo debe ser posterior al inicio.")
            return redirect('capturar_ventas_contrato', contrato_id=contrato_id)

        try:
            monto_ventas = Decimal(monto_ventas_str)
        except (InvalidOperation, TypeError):
            messages.error(request, "El monto de ventas capturado no es válido.")
            return redirect('capturar_ventas_contrato', contrato_id=contrato_id)

        if monto_ventas < 0:
            messages.error(request, "El monto de ventas no puede ser negativo.")
            return redirect('capturar_ventas_contrato', contrato_id=contrato_id)

        porcentaje_aplicado = contrato.porcentaje_ventas or Decimal('0')  # noqa: FURB157
        renta_variable_calculada = (monto_ventas * porcentaje_aplicado / Decimal('100')).quantize(Decimal('0.01'))  # noqa: FURB157

        if contrato.tipo_renta == 'mixta':
            renta_base_del_periodo = contrato.cuota
        else:
            renta_base_del_periodo = Decimal('0')  # noqa: FURB157

        total_a_cobrar = renta_base_del_periodo + renta_variable_calculada

        if contrato.tipo_renta == 'variable' and contrato.cuota and total_a_cobrar < contrato.cuota:
            total_a_cobrar = contrato.cuota

        # NUEVO -- si el contrato incluye mantenimiento, se suma aparte
        # al total a cobrar (independiente del tipo de renta).
        if contrato.incluye_mantenimiento and contrato.cuota_mantenimiento:
            total_a_cobrar += contrato.cuota_mantenimiento

        ReporteVentasContrato.objects.create(
            contrato=contrato,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            monto_ventas=monto_ventas,
            porcentaje_aplicado=porcentaje_aplicado,
            renta_variable_calculada=renta_variable_calculada,
            renta_base_del_periodo=renta_base_del_periodo,
            total_a_cobrar=total_a_cobrar,
            capturado_por=request.user,
        )

        messages.success(
            request,
            f"Ventas capturadas -- renta a cobrar de este periodo: ${total_a_cobrar}. "
            f"Genera la factura manualmente en Facturación por ese monto."
        )
        return redirect('capturar_ventas_contrato', contrato_id=contrato_id)

    reportes = contrato.reportes_ventas.all()
    return render(request, 'arrendamientos/capturar_ventas.html', {
        'contrato': contrato,
        'reportes': reportes,
    })



BANXICO_SERIE_INPC = "SP1"


def obtener_inpc(fecha):
    """Consulta el valor del INPC (serie SP1, Banxico) publicado mas
    cercano a la fecha dada -- el INPC se publica quincenal/mensualmente,
    asi que se consulta un rango de 45 dias hacia atras y se toma el
    valor mas reciente disponible dentro de ese rango. Devuelve un
    Decimal, o None si no se pudo consultar (sin token, sin internet,
    fecha fuera de rango, etc.)."""
    token = getattr(settings, 'BANXICO_TOKEN', '')
    if not token:
        return None

    fecha_desde = (fecha - timedelta(days=45)).strftime('%Y-%m-%d')
    fecha_hasta = fecha.strftime('%Y-%m-%d')
    url = (
        f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/"
        f"{BANXICO_SERIE_INPC}/datos/{fecha_desde}/{fecha_hasta}"
    )

    try:
        response = requests.get(url, headers={'Bmx-Token': token}, timeout=10)
        response.raise_for_status()
        datos = response.json()
        serie = datos['bmx']['series'][0]['datos']
        if not serie:
            return None
        return Decimal(serie[-1]['dato'])
    except Exception:  # noqa: BLE001 -- cualquier falla de red/formato -> None
        return None


def calcular_incremento_inpc(fecha_base, fecha_actual=None):
    """Calcula el % de incremento segun la variacion del INPC entre
    fecha_base (normalmente la fecha de inicio del contrato) y hoy (o
    fecha_actual). Devuelve None si no se pudo consultar el INPC en
    alguna de las 2 fechas."""
    fecha_actual = fecha_actual or date.today()  # noqa: DTZ011
    inpc_base = obtener_inpc(fecha_base)
    inpc_actual = obtener_inpc(fecha_actual)

    if not inpc_base or not inpc_actual or inpc_base == 0:
        return None

    porcentaje = ((inpc_actual / inpc_base) - Decimal('1')) * Decimal('100')  # noqa: FURB157
    return porcentaje.quantize(Decimal('0.01'))


@login_required
def renovar_contrato_simple(request, contrato_id):
    contrato_actual = get_object_or_404(ContratoArea, id=contrato_id, estatus='vigente')
    area = contrato_actual.area
    nueva_fecha_inicio = contrato_actual.fecha_fin + timedelta(days=1)
 
    if request.method == 'POST':
        plazo_str = request.POST.get('plazo_forzoso_meses', '').strip()
        try:
            plazo_forzoso_meses = int(plazo_str)
            if plazo_forzoso_meses < 1:
                raise ValueError
        except ValueError:
            messages.error(request, "El plazo capturado no es válido.")
            return redirect('renovar_contrato_simple', contrato_id=contrato_id)
 
        mes_objetivo = nueva_fecha_inicio + relativedelta(months=plazo_forzoso_meses - 1)
        ultimo_dia = calendar.monthrange(mes_objetivo.year, mes_objetivo.month)[1]
        nueva_fecha_fin = mes_objetivo.replace(day=ultimo_dia)
 
        with transaction.atomic():
            contrato_actual.estatus = 'renovado'
            contrato_actual.save(update_fields=['estatus'])
 
            nuevo_contrato = ContratoArea.objects.create(
                area=area,
                cliente=contrato_actual.cliente,
                giro=contrato_actual.giro,
                fecha_firma=nueva_fecha_inicio,
                fecha_inicio=nueva_fecha_inicio,
                fecha_fin=nueva_fecha_fin,
                cuota=contrato_actual.cuota,
                deposito=contrato_actual.deposito,
                plazo_forzoso_meses=plazo_forzoso_meses,
                renovacion_automatica=contrato_actual.renovacion_automatica,
                tipo_incremento=contrato_actual.tipo_incremento,
                porcentaje_incremento=contrato_actual.porcentaje_incremento,
                periodicidad_facturacion=contrato_actual.periodicidad_facturacion,
                tipo_renta=contrato_actual.tipo_renta,
                porcentaje_ventas=contrato_actual.porcentaje_ventas,
                incluye_mantenimiento=contrato_actual.incluye_mantenimiento,
                cuota_mantenimiento=contrato_actual.cuota_mantenimiento,
                penalizacion_atraso_porcentaje=contrato_actual.penalizacion_atraso_porcentaje,
                estatus_deposito=contrato_actual.estatus_deposito,
                clausulas_especiales=contrato_actual.clausulas_especiales,
                contrato_anterior=contrato_actual,
                creado_por=request.user,
            )
            nuevo_contrato.sincronizar_a_area()
 
        mensaje_base = (
            f"Contrato del área {area.numero} renovado hasta "
            f"{nueva_fecha_fin.strftime('%d/%m/%Y')}, mismas condiciones que el anterior."
        )
        try:
            generar_facturas_area(area)
            messages.success(request, f"{mensaje_base} Se generó su facturación inicial.")
        except Exception as e:  # noqa: BLE001
            messages.warning(
                request,
                f"{mensaje_base} El contrato se guardó correctamente, pero no se pudo generar "
                f"la facturación inicial ({e})."
            )
 
        return redirect('historial_contratos_area', area_id=area.id)
 
    return render(request, 'arrendamientos/renovar_simple.html', {
        'contrato': contrato_actual,
        'nueva_fecha_inicio': nueva_fecha_inicio,
    })


@login_required
def preparar_renovacion(request, contrato_id, modo):
    """Calcula todos los datos del contrato renovado (fechas, plazo, y
    la cuota con incremento si aplica) SIN guardar nada -- muestra el
    formulario completo de contrato ya lleno, para que el usuario lo
    revise y confirme. El guardado real lo sigue haciendo
    crear_contrato_area (su POST ya detecta y renueva el contrato
    vigente automaticamente)."""
    contrato_actual = get_object_or_404(ContratoArea, id=contrato_id, estatus__in=['vigente', 'vencido_ocupado'])
    area = contrato_actual.area
    nueva_fecha_inicio = contrato_actual.fecha_fin + timedelta(days=1)
    plazo = contrato_actual.plazo_forzoso_meses or 12
 
    if modo == 'porcentaje_fijo':
        if contrato_actual.tipo_incremento != 'porcentaje_fijo':
            messages.error(request, "Este contrato no tiene un % de incremento fijo pactado.")
            return redirect('historial_contratos_area', area_id=area.id)
        porcentaje = contrato_actual.porcentaje_incremento or Decimal('0')  # noqa: FURB157
        factor = Decimal('1') + (porcentaje / Decimal('100'))  # noqa: FURB157
        nueva_cuota = (contrato_actual.cuota * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
 
    elif modo == 'inpc':
        if contrato_actual.tipo_incremento != 'inpc':
            messages.error(request, "Este contrato no tiene incremento por INPC pactado.")
            return redirect('historial_contratos_area', area_id=area.id)
        porcentaje = calcular_incremento_inpc(contrato_actual.fecha_inicio)
        if porcentaje is None:
            messages.error(
                request,
                "No se pudo consultar el INPC en este momento -- intenta de nuevo más tarde, "
                "o renueva con \"Renovar contrato\" y captura el % a mano."
            )
            return redirect('historial_contratos_area', area_id=area.id)
        factor = Decimal('1') + (porcentaje / Decimal('100'))  # noqa: FURB157
        nueva_cuota = (contrato_actual.cuota * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
 
    else:  # 'simple' -- mismas condiciones, sin incremento
        nueva_cuota = contrato_actual.cuota
 
    mes_objetivo = nueva_fecha_inicio + relativedelta(months=plazo - 1)
    ultimo_dia = calendar.monthrange(mes_objetivo.year, mes_objetivo.month)[1]
    nueva_fecha_fin = mes_objetivo.replace(day=ultimo_dia)
 
    borrador = {
        'cliente_id': contrato_actual.cliente_id,
        'giro': contrato_actual.giro or '',
        'fecha_firma': nueva_fecha_inicio,
        'fecha_inicio': nueva_fecha_inicio,
        'fecha_fin': nueva_fecha_fin,
        'plazo_forzoso_meses': plazo,
        'cuota': nueva_cuota,
        'deposito': contrato_actual.deposito,
        'renovacion_automatica': contrato_actual.renovacion_automatica,
        'tipo_incremento': contrato_actual.tipo_incremento,
        'porcentaje_incremento': contrato_actual.porcentaje_incremento,
        'periodicidad_facturacion': contrato_actual.periodicidad_facturacion,
        'tipo_renta': contrato_actual.tipo_renta,
        'porcentaje_ventas': contrato_actual.porcentaje_ventas,
        'incluye_mantenimiento': contrato_actual.incluye_mantenimiento,
        'cuota_mantenimiento': contrato_actual.cuota_mantenimiento,
        'penalizacion_atraso_porcentaje': contrato_actual.penalizacion_atraso_porcentaje,
        'clausulas_especiales': contrato_actual.clausulas_especiales or '',
    }
 
    return render(request, 'arrendamientos/crear_contrato.html', {
        'area': area,
        'contrato_vigente': contrato_actual,
        'borrador': borrador,
        'es_borrador_renovacion': True,
        'tipo_incremento_choices': ContratoArea.TIPO_INCREMENTO_CHOICES,
        'tipo_renta_choices': ContratoArea.TIPO_RENTA_CHOICES,
        'periodicidad_choices': ContratoArea.PERIODICIDAD_CHOICES,
        'clientes': Cliente.objects.filter(empresa=area.empresa, activo=True).order_by('nombre'),
    })

