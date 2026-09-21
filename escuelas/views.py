
import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import xlrd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from escuelas.metricas import calcular_metricas_alumnos
from gastos.models import Gasto
from principal.models import ConfiguracionMembresia

from .decoradores import requiere_membresia_activa_escuela
from .models import IngresoEscuela, SolicitudAdmision

#constantes de columnas para el archivo Excel de FiServ
COL_FECHA = 2
COL_RESULTADO = 6
COL_MONTO = 9
COL_FORMA_PAGO = 10
COL_ALUMNO = 13
COL_MATRICULA = 14
COL_CONCEPTO = 15

#   Estas constantes representan las columnas específicas en el archivo Excel exportado desde FiServ.
PREFIJOS_IGNORAR = ('Sub Total', 'Gran Total', 'Página', 'Pagina')

# NUEVO -- % de comision que descuenta el comisionista de la plataforma.
# Es un valor TEMPORAL (2%, redondeado desde el 1.83% real observado)
# mientras se confirma el porcentaje exacto -- ajusta este unico valor
# cuando lo tengas, y los NUEVOS registros importados ya lo usaran
# correctamente (los ya importados conservan el % que se les aplico).
PORCENTAJE_COMISION_FISERV = Decimal('2.00')

# Nombres de los meses para mostrar en la interfaz de usuario.
MESES_NOMBRES = [  
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]

MESES_ABREVIADOS = [  
    '', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]

def _ultimos_n_meses(fecha_ref, n=6):
    meses = []
    anio, mes = fecha_ref.year, fecha_ref.month
    for _ in range(n):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1
    return list(reversed(meses))


@login_required
@requiere_membresia_activa_escuela
def importar_ingresos_excel(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, "Selecciona un archivo Excel.")
            return redirect('importar_ingresos_excel')
 
        try:
            wb = xlrd.open_workbook(file_contents=archivo.read())
            hoja = wb.sheet_by_index(0)
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                f"No se pudo leer el archivo -- verifica que sea el reporte .xls exportado de Academic+ ({e}).",
            )
            return redirect('importar_ingresos_excel')
 
        creados = 0
        errores = []
        forma_pago_actual = None
 
        with transaction.atomic():
            for i in range(hoja.nrows):
                valores_fila = [hoja.cell(i, col).value for col in range(hoja.ncols)]
                no_vacios = [v for v in valores_fila if v != '']
 
                if not no_vacios:
                    continue
 
                primer_valor = valores_fila[0]
 
                if (
                    len(no_vacios) == 1
                    and isinstance(primer_valor, str)
                    and not primer_valor.startswith(PREFIJOS_IGNORAR)
                ):
                    forma_pago_actual = primer_valor.strip()
                    continue
 
                if isinstance(primer_valor, str) and primer_valor.startswith(PREFIJOS_IGNORAR):
                    continue
 
                if primer_valor == 'Recibo':
                    continue
 
                if not primer_valor or hoja.ncols < 9:
                    continue
 
                concepto = valores_fila[3]
                nombre_alumno = valores_fila[2]
                matricula = valores_fila[1]
                fecha_raw = valores_fila[7]
                importe_raw = valores_fila[8]
 
                if not concepto or importe_raw == '':
                    continue
 
                try:
                    fecha = xlrd.xldate_as_datetime(fecha_raw, wb.datemode).date()
                except (ValueError, TypeError):
                    errores.append(f"Fila {i + 1}: fecha inválida ('{fecha_raw}').")
                    continue
 
                try:
                    monto = Decimal(str(importe_raw))
                except (InvalidOperation, TypeError):
                    errores.append(f"Fila {i + 1}: monto inválido ('{importe_raw}').")
                    continue
 
                if monto <= 0:
                    continue
 
                concepto_upper = str(concepto).upper()
                if concepto_upper.startswith('COLEGIATURA'):
                    categoria = 'colegiatura'
                elif concepto_upper.startswith('INSCRIP'):
                    categoria = 'inscripcion'
                else:
                    categoria = 'otro'
 
                IngresoEscuela.objects.create(
                    empresa=perfil.empresa,
                    fecha=fecha,
                    concepto=str(concepto).strip(),
                    categoria=categoria,
                    monto=monto,
                    forma_pago=forma_pago_actual,
                    alumno=str(nombre_alumno).strip() if nombre_alumno else None,
                    matricula=str(matricula).strip() if matricula else None,
                    origen='cobranza',
                    importado_por=request.user,
                    archivo_origen=archivo.name,
                )
                creados += 1
 
        if creados:
            messages.success(request, f"Se importaron {creados} ingreso(s) correctamente.")
        if errores:
            mensaje_errores = " | ".join(errores[:10])
            if len(errores) > 10:
                mensaje_errores += f" ... y {len(errores) - 10} más."
            messages.warning(request, f"{len(errores)} fila(s) con errores, se omitieron: {mensaje_errores}")
        if not creados and not errores:
            messages.warning(request, "El archivo no tenía filas con datos para importar.")
 
        return redirect('importar_ingresos_excel')
 
    ingresos_recientes = IngresoEscuela.objects.filter(empresa=perfil.empresa)[:20]
    return render(request, 'escuelas/importar_ingresos.html', {
        'ingresos_recientes': ingresos_recientes,
    })


@login_required
@requiere_membresia_activa_escuela
def importar_ingresos_fiserv(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, "Selecciona un archivo Excel.")
            return redirect('importar_ingresos_fiserv')
 
        try:
            wb = xlrd.open_workbook(file_contents=archivo.read())
            hoja = wb.sheet_by_index(0)
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                f"No se pudo leer el archivo -- verifica que sea el reporte de la plataforma Academic ({e}).",
            )
            return redirect('importar_ingresos_fiserv')
 
        creados = 0
        omitidos_no_aprobados = 0
        errores = []
 
        with transaction.atomic():
            for i in range(1, hoja.nrows):
                if hoja.ncols <= COL_CONCEPTO:
                    continue
 
                resultado = hoja.cell(i, COL_RESULTADO).value
                alumno = hoja.cell(i, COL_ALUMNO).value
                monto_raw = hoja.cell(i, COL_MONTO).value
 
                if not alumno or monto_raw == '':
                    continue
 
                if resultado != 'APROBADO':
                    omitidos_no_aprobados += 1
                    continue
 
                if 'PRUEBA' in str(alumno).upper():
                    continue
 
                fecha_raw = hoja.cell(i, COL_FECHA).value
                concepto = hoja.cell(i, COL_CONCEPTO).value
                matricula = hoja.cell(i, COL_MATRICULA).value
                merchant_id = hoja.cell(i, COL_FORMA_PAGO).value
 
                try:
                    fecha = xlrd.xldate_as_datetime(fecha_raw, wb.datemode).date()
                except (ValueError, TypeError):
                    errores.append(f"Fila {i + 1}: fecha inválida ('{fecha_raw}').")
                    continue
 
                try:
                    monto = Decimal(str(monto_raw))
                except (InvalidOperation, TypeError):
                    errores.append(f"Fila {i + 1}: monto inválido ('{monto_raw}').")
                    continue
 
                if monto <= 0:
                    continue

                # NUEVO -- calcula la comision de la plataforma sobre
                # el monto bruto de esta transaccion.
                comision = (monto * PORCENTAJE_COMISION_FISERV / Decimal('100')).quantize(Decimal('0.01'))  # noqa: FURB157

                concepto_upper = str(concepto).upper()
                if 'COLEGIATURA' in concepto_upper:
                    categoria = 'colegiatura'
                elif 'INSCRIP' in concepto_upper:
                    categoria = 'inscripcion'
                else:
                    categoria = 'otro'
 
                IngresoEscuela.objects.create(
                    empresa=perfil.empresa,
                    fecha=fecha,
                    concepto=str(concepto).strip() if concepto else '',
                    categoria=categoria,
                    monto=monto,
                    comision=comision,
                    porcentaje_comision_aplicado=PORCENTAJE_COMISION_FISERV,
                    forma_pago=str(merchant_id).strip() if merchant_id else None,
                    alumno=str(alumno).strip(),
                    matricula=str(matricula).strip() if matricula else None,
                    origen='fiserv',
                    importado_por=request.user,
                    archivo_origen=archivo.name,
                )
                creados += 1
 
        if creados:
            messages.success(
                request,
                f"Se importaron {creados} pago(s) aprobado(s). "
                f"Se omitieron {omitidos_no_aprobados} intento(s) no aprobado(s) o incompleto(s).",
            )
        if errores:
            mensaje_errores = " | ".join(errores[:10])
            if len(errores) > 10:
                mensaje_errores += f" ... y {len(errores) - 10} más."
            messages.warning(request, f"{len(errores)} fila(s) con errores, se omitieron: {mensaje_errores}")
        if not creados and not errores:
            messages.warning(request, "El archivo no tenía pagos aprobados para importar.")
 
        return redirect('importar_ingresos_fiserv')
 
    ingresos_recientes = IngresoEscuela.objects.filter(empresa=perfil.empresa, origen='fiserv')[:20]
    return render(request, 'escuelas/importar_ingresos_fiserv.html', {
        'ingresos_recientes': ingresos_recientes,
    })


@login_required
@requiere_membresia_activa_escuela
def dashboard_inicio_escuela(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
        return redirect('dashboard_inicio')
 
    empresa = perfil.empresa
    hoy = date.today()
 
    try:
        mes_sel = int(request.GET.get('mes', hoy.month))
        anio_sel = int(request.GET.get('anio', hoy.year))
        if mes_sel < 1 or mes_sel > 12:
            mes_sel = hoy.month
            anio_sel = hoy.year
    except (TypeError, ValueError):
        mes_sel = hoy.month
        anio_sel = hoy.year
 
    fecha_referencia = date(anio_sel, mes_sel, 1)
 
    ingresos_mes_actual = IngresoEscuela.objects.filter(
        empresa=empresa, fecha__year=anio_sel, fecha__month=mes_sel,
    ).aggregate(total=Sum('monto'))['total'] or 0
 
    ingresos_acumulados = IngresoEscuela.objects.filter(
        empresa=empresa,
    ).aggregate(total=Sum('monto'))['total'] or 0
 
    ingresos_por_categoria = (
        IngresoEscuela.objects.filter(empresa=empresa, fecha__year=anio_sel, fecha__month=mes_sel)
        .values('categoria')
        .annotate(total=Sum('monto'))
        .order_by('-total')
    )
 
    resumen_fiserv_mes = IngresoEscuela.objects.filter(
        empresa=empresa, origen='fiserv', fecha__year=anio_sel, fecha__month=mes_sel,
    ).aggregate(bruto=Sum('monto'), comision=Sum('comision'))
    ingreso_bruto_plataforma = resumen_fiserv_mes['bruto'] or Decimal('0')
    comision_plataforma = resumen_fiserv_mes['comision'] or Decimal('0')
    ingreso_neto_plataforma = ingreso_bruto_plataforma - comision_plataforma
 
    metricas_alumnos = calcular_metricas_alumnos(empresa, fecha_referencia=fecha_referencia)
 
    primer_registro = IngresoEscuela.objects.filter(empresa=empresa).order_by('fecha').first()
    anio_min = primer_registro.fecha.year if primer_registro else hoy.year
    anios_disponibles = list(range(anio_min, hoy.year + 1))
 
    rango_6_meses = _ultimos_n_meses(fecha_referencia, n=6)
    labels_grafico = [f"{MESES_ABREVIADOS[m]} {a}" for a, m in rango_6_meses]
    fecha_inicio_rango = date(rango_6_meses[0][0], rango_6_meses[0][1], 1)
 
    ingresos_qs = (
        IngresoEscuela.objects.filter(empresa=empresa, fecha__gte=fecha_inicio_rango)
        .annotate(mes_trunc=TruncMonth('fecha'))
        .values('mes_trunc')
        .annotate(total=Sum('monto'))
    )
    ingresos_dict = {
        (x['mes_trunc'].year, x['mes_trunc'].month): float(x['total'] or 0)
        for x in ingresos_qs
    }
 
    gastos_qs = (
        Gasto.objects.filter(empresa=empresa, fecha__gte=fecha_inicio_rango)
        .exclude(estatus='cancelada')
        .annotate(mes_trunc=TruncMonth('fecha'))
        .values('mes_trunc')
        .annotate(total=Sum('monto'))
    )
    gastos_dict = {
        (x['mes_trunc'].year, x['mes_trunc'].month): float(x['total'] or 0)
        for x in gastos_qs
    }
 
    datos_ingresos = [ingresos_dict.get((a, m), 0) for a, m in rango_6_meses]
    datos_gastos = [gastos_dict.get((a, m), 0) for a, m in rango_6_meses]
 
    return render(request, 'escuelas/dashboard_inicio_escuela.html', {
        'empresa': empresa,
        'mes_sel': mes_sel,
        'anio_sel': anio_sel,
        'meses_nombres': MESES_NOMBRES,
        'anios_disponibles': anios_disponibles,
        'es_mes_actual': (mes_sel == hoy.month and anio_sel == hoy.year),
        'ingresos_mes_actual': ingresos_mes_actual,
        'ingresos_acumulados': ingresos_acumulados,
        'ingresos_por_categoria': ingresos_por_categoria,
        'ingreso_bruto_plataforma': ingreso_bruto_plataforma,
        'comision_plataforma': comision_plataforma,
        'ingreso_neto_plataforma': ingreso_neto_plataforma,
        'metricas_alumnos': metricas_alumnos,
        'labels_grafico': labels_grafico,
        'datos_ingresos': datos_ingresos,
        'datos_gastos': datos_gastos,
    })


@login_required
def membresia_vencida_escuela(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    return render(request, 'escuelas/membresia_vencida.html', {
        'perfil': perfil,
        'config': ConfiguracionMembresia.obtener(),
    })


@login_required
@requiere_membresia_activa_escuela
def dashboard_admisiones(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
        return redirect('dashboard_inicio')
 
    empresa = perfil.empresa
    solicitudes = SolicitudAdmision.objects.filter(empresa=empresa)
 
    conteo_por_etapa = []
    for valor, etiqueta in SolicitudAdmision.ETAPA_CHOICES:
        conteo_por_etapa.append({
            'etapa': valor,
            'etiqueta': etiqueta,
            'total': solicitudes.filter(etapa=valor).count(),
        })
 
    return render(request, 'escuelas/dashboard_admisiones.html', {
        'empresa': empresa,
        'conteo_por_etapa': conteo_por_etapa,
        'total_solicitudes': solicitudes.count(),
        'solicitudes_recientes': solicitudes[:30],
    })
















### Webhook HubSpot Admisiones######

logger = logging.getLogger(__name__)


MAPEO_ETAPAS_HUBSPOT = {
    # "id_real_de_hubspot": "prospecto",
    # "id_real_de_hubspot": "contacto",
    # "id_real_de_hubspot": "visita_agendada",
    # "id_real_de_hubspot": "visita_realizada",
    # "id_real_de_hubspot": "solicitud",
    # "id_real_de_hubspot": "inscrito",
}


def _extraer_valor(diccionario, *claves_posibles):
    for clave in claves_posibles:
        valor = diccionario.get(clave)
        if isinstance(valor, dict):
            valor = valor.get('value')
        if valor:
            return valor
    return None


@csrf_exempt
@require_POST
def webhook_hubspot_admisiones(request, token, empresa_id):
    if token != settings.HUBSPOT_WEBHOOK_TOKEN:
        return JsonResponse({'error': 'token invalido'}, status=403)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'JSON invalido'}, status=400)

    logger.info("Webhook HubSpot recibido: %s", json.dumps(payload)[:2000])

    if isinstance(payload, list):
        payload = payload[0] if payload else {}

    propiedades = payload.get('properties', payload)

    deal_id = str(
        payload.get('objectId')
        or payload.get('dealId')
        or payload.get('deal_id')
        or _extraer_valor(propiedades, 'hs_object_id')
        or ''
    )
    if not deal_id:
        return JsonResponse({'error': 'no se encontro el ID del deal en el payload'}, status=400)

    etapa_id_hubspot = _extraer_valor(propiedades, 'dealstage', 'deal_stage')
    etapa = MAPEO_ETAPAS_HUBSPOT.get(etapa_id_hubspot, 'prospecto')
    if etapa_id_hubspot and etapa_id_hubspot not in MAPEO_ETAPAS_HUBSPOT:
        logger.warning("Etapa de HubSpot sin mapear todavia: %s", etapa_id_hubspot)

    solicitud, _creado = SolicitudAdmision.objects.update_or_create(
        hubspot_deal_id=deal_id,
        defaults={
            'empresa_id': empresa_id,
            'nombre_contacto': _extraer_valor(propiedades, 'dealname', 'nombre', 'firstname'),
            'telefono': _extraer_valor(propiedades, 'phone', 'telefono'),
            'email': _extraer_valor(propiedades, 'email'),
            'nivel_de_interes': _extraer_valor(propiedades, 'nivel_de_interes'),
            'mensaje': _extraer_valor(propiedades, 'mensaje', 'message'),
            'etapa': etapa,
            'payload_crudo': payload,
        },
    )

    return JsonResponse({'ok': True, 'solicitud_id': solicitud.id})