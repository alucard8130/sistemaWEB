
import datetime
import json
import locale
import logging
from calendar import month_name
from collections import OrderedDict
from datetime import date
from decimal import Decimal

import xlrd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from caja_chica.models import FondeoCajaChica
from conciliaciones.utils import calcular_saldo_acumulado_hasta
from empresas.models import CuentaBancaria
from gastos.models import Gasto
from principal.models import ConfiguracionMembresia

from .decoradores import requiere_membresia_activa_escuela
from .ingresos_utils import COMISION_REFERENCIA, tipo_tarjeta_merchant
from .models import (
    Alumno,
    CarteraVencida,
    IngresoEscuela,
    LoteImportacionIngresos,
    PresupuestoIngresoEscuela,
    SolicitudAdmision,
)

# NUEVO -- los importadores de ingresos (Detalle de Pagos -> bancos / caja chica)
# y el cuadre con Fiserv viven ahora en views_ingresos.py. Se re-exportan aqui
# para que cualquier import existente (from escuelas.views import ...) siga funcionando.
from .views_ingresos import (  # noqa: F401
    importar_ingresos_excel,
    importar_ingresos_fiserv,
)

# NUEVO -- interruptor. Los ingresos con origen='fiserv' (importador ANTERIOR)
# repiten pagos con tarjeta que ya vienen en el Detalle de Pagos. Mientras sea
# False, dashboard / presupuesto / estado de resultados se comportan EXACTAMENTE
# como antes. Ponlo en True cuando hayas borrado o decidido ignorar esos registros
# antiguos para no contar dos veces los pagos con tarjeta.
EXCLUIR_INGRESOS_FISERV_LEGADO = False


def _ingresos_base(empresa):
    qs = IngresoEscuela.objects.filter(empresa=empresa)
    if EXCLUIR_INGRESOS_FISERV_LEGADO:
        qs = qs.exclude(origen='fiserv')
    return qs

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

NIVELES_VALIDOS = {'PREESCOLAR': 'preescolar', 'PRIMARIA': 'primaria'}

### Funciones auxiliares para manejo de fechas y meses ###
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




## Importadores de ingresos (Detalle de Pagos) y cuadre Fiserv: ver views_ingresos.py ##


####funciones para importar el roster de alumnos desde Excel
def _parsear_roster(wb):
    sheet = wb.sheet_by_index(0)
    alumnos = []
    nivel_actual = None
    grado_actual = None
    grupo_actual = None
    turno_actual = None
 
    for fila in range(sheet.nrows):
        valores = [sheet.cell(fila, col).value for col in range(sheet.ncols)]
        col0 = valores[0]
        col1 = valores[1] if len(valores) > 1 else ''
 
        if col1 == 'Nivel:':
            nivel_raw = str(valores[2]).strip().upper() if len(valores) > 2 else ''
            nivel_actual = NIVELES_VALIDOS.get(nivel_raw, nivel_actual)
            grado_actual = valores[4] if len(valores) > 4 else None
            if len(valores) > 6 and valores[5] == 'Grupo:':
                grupo_actual = valores[6]
            else:
                grupo_actual = None
            turno_actual = valores[8] if len(valores) > 8 and valores[7] == 'Turno:' else None
            continue
 
        if col1 == 'Grupo:':
            grupo_actual = valores[2] if len(valores) > 2 else None
            turno_actual = valores[8] if len(valores) > 8 and valores[7] == 'Turno:' else turno_actual
            continue
 
        if col0 == 'Liceo Real del Valle':
            continue
        if isinstance(col0, str) and col0.startswith('TOTAL'):
            continue
        if not any(valores):
            continue
        if col0 == 'Número' or col1 == 'Matricula':
            continue
 
        if isinstance(col0, float) and col1 and valores[2]:
            alumnos.append({
                'matricula': str(col1).strip(),
                'nombre': str(valores[2]).strip(),
                'nivel': nivel_actual,
                'grado': grado_actual,
                'grupo': grupo_actual,
                'turno': turno_actual,
            })
 
    return alumnos
 
 
@login_required
@requiere_membresia_activa_escuela
def importar_roster_alumnos(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, "Selecciona un archivo Excel.")
            return redirect('importar_roster_alumnos')
 
        try:
            wb = xlrd.open_workbook(file_contents=archivo.read())
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                f"No se pudo leer el archivo -- verifica que sea el reporte 'Alumnos por Grupo' de Academic+ ({e}).",
            )
            return redirect('importar_roster_alumnos')
 
        alumnos_parseados = _parsear_roster(wb)
        if not alumnos_parseados:
            messages.warning(request, "El archivo no tenía alumnos para importar.")
            return redirect('importar_roster_alumnos')
 
        nivel_del_archivo = alumnos_parseados[0]['nivel']
        hoy = date.today()  # noqa: DTZ011
 
        with transaction.atomic():
            matriculas_en_archivo = set()
            creados = 0
            actualizados = 0
 
            for a in alumnos_parseados:
                matriculas_en_archivo.add(a['matricula'])
                _obj, creado = Alumno.objects.update_or_create(
                    empresa=perfil.empresa,
                    matricula=a['matricula'],
                    defaults={
                        'nombre': a['nombre'],
                        'nivel': a['nivel'],
                        'grado': a['grado'],
                        'grupo': a['grupo'],
                        'turno': a['turno'],
                        'activo': True,
                        'fecha_ultimo_visto': hoy,
                        'fecha_baja_detectada': None,
                    },
                )
                if creado:
                    creados += 1
                else:
                    actualizados += 1
 
            bajas = (
                Alumno.objects.filter(empresa=perfil.empresa, nivel=nivel_del_archivo, activo=True)
                .exclude(matricula__in=matriculas_en_archivo)
            )
            total_bajas = bajas.count()
            bajas.update(activo=False, fecha_baja_detectada=hoy)
 
        mensaje = f"Roster de {nivel_del_archivo} actualizado -- {creados} alumno(s) nuevo(s), {actualizados} actualizado(s)."
        if total_bajas:
            mensaje += f" {total_bajas} alumno(s) ya no aparecen en el roster y se marcaron como baja."
        messages.success(request, mensaje)
        return redirect('importar_roster_alumnos')
 
    total_activos = Alumno.objects.filter(empresa=perfil.empresa, activo=True).count()
    total_preescolar = Alumno.objects.filter(empresa=perfil.empresa, activo=True, nivel='preescolar').count()
    total_primaria = Alumno.objects.filter(empresa=perfil.empresa, activo=True, nivel='primaria').count()
    bajas_recientes = Alumno.objects.filter(empresa=perfil.empresa, activo=False).order_by('-fecha_baja_detectada')[:10]
 
    return render(request, 'escuelas/importar_roster_alumnos.html', {
        'total_activos': total_activos,
        'total_preescolar': total_preescolar,
        'total_primaria': total_primaria,
        'bajas_recientes': bajas_recientes,
    })



### Funciones para importar altas de alumnos
def _parsear_altas(wb):
    sheet = wb.sheet_by_index(0)
    altas = []
    nivel_actual = None
    grupo_actual = None
 
    for fila in range(sheet.nrows):
        valores = [sheet.cell(fila, col).value for col in range(sheet.ncols)]
        col1 = str(valores[1]) if len(valores) > 1 else ''
 
        if col1.startswith('Nivel:'):
            nivel_raw = col1.replace('Nivel:', '').strip().upper()
            nivel_actual = NIVELES_VALIDOS.get(nivel_raw, nivel_actual)
            continue
 
        if col1.startswith('Grupo'):
            grupo_actual = col1.split(':', 1)[1].strip() if ':' in col1 else None
            continue
 
        if col1 == 'Matricula':
            continue
        if not any(valores):
            continue
 
        matricula = valores[1] if len(valores) > 1 else None
        nombre = valores[2] if len(valores) > 2 else None
        fecha_raw = valores[3] if len(valores) > 3 else None
 
        if matricula and nombre and isinstance(fecha_raw, float):
            fecha_alta = xlrd.xldate_as_datetime(fecha_raw, wb.datemode).date()
            altas.append({
                'matricula': str(matricula).strip(),
                'nombre': str(nombre).strip(),
                'nivel': nivel_actual,
                'grupo': grupo_actual,
                'fecha_alta': fecha_alta,
            })
 
    return altas
 
 
@login_required
@requiere_membresia_activa_escuela
def importar_altas_alumnos(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, "Selecciona un archivo Excel.")
            return redirect('importar_altas_alumnos')
 
        try:
            wb = xlrd.open_workbook(file_contents=archivo.read())
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                f"No se pudo leer el archivo -- verifica que sea el reporte 'Altas por Ciclo' de Academic+ ({e}).",
            )
            return redirect('importar_altas_alumnos')
 
        altas_parseadas = _parsear_altas(wb)
        if not altas_parseadas:
            messages.warning(request, "El archivo no tenía altas para importar.")
            return redirect('importar_altas_alumnos')
 
        creados = 0
        actualizados = 0
 
        with transaction.atomic():
            for a in altas_parseadas:
                _obj, creado = Alumno.objects.update_or_create(
                    empresa=perfil.empresa,
                    matricula=a['matricula'],
                    defaults={
                        'nombre': a['nombre'],
                        'nivel': a['nivel'],
                        'grupo': a['grupo'],
                        'fecha_alta': a['fecha_alta'],
                        'activo': True,
                    },
                )
                if creado:
                    creados += 1
                else:
                    actualizados += 1
 
        messages.success(
            request,
            f"Altas importadas -- {creados} alumno(s) nuevo(s) creado(s), "
            f"{actualizados} ya existente(s) con su fecha de alta actualizada.",
        )
        return redirect('importar_altas_alumnos')
 
    altas_recientes = Alumno.objects.filter(
        empresa=perfil.empresa, fecha_alta__isnull=False,
    ).order_by('-fecha_alta')[:20]
 
    return render(request, 'escuelas/importar_altas_alumnos.html', {
        'altas_recientes': altas_recientes,
    })


### Funciones auxiliares para importar deudores y cartera vencida
def _parsear_deudores(wb):
    sheet = wb.sheet_by_index(0)
    deudores = []
    alumno_actual = None
 
    for fila in range(1, sheet.nrows):
        valores = [sheet.cell(fila, col).value for col in range(sheet.ncols)]
        valores = (valores + [None] * 4)[:4]
        col0, col1, col2, col3 = valores  # noqa: RUF059
 
        if isinstance(col0, str) and (col0.startswith('GRAN TOTAL') or col0.startswith('Página')):  # noqa: PIE810
            continue
        if not any(valores):
            continue
 
        if col2:
            alumno_actual = {
                'matricula': str(col0).strip(),
                'nombre': str(col1).strip(),
                'grupo': str(col2).strip(),
            }
            continue
 
        if alumno_actual and isinstance(col0, str) and isinstance(col1, (int, float)):
            deudores.append({
                **alumno_actual,
                'concepto': col0.strip(),
                'monto': col1,
            })
 
    return deudores
 
 
@login_required
@requiere_membresia_activa_escuela
def importar_cartera_vencida(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        fecha_corte_raw = request.POST.get('fecha_corte')
 
        if not archivo:
            messages.error(request, "Selecciona un archivo Excel.")
            return redirect('importar_cartera_vencida')
 
        try:
            fecha_corte = date.fromisoformat(fecha_corte_raw) if fecha_corte_raw else date.today()  # noqa: DTZ011
        except ValueError:
            fecha_corte = date.today()  # noqa: DTZ011
 
        try:
            wb = xlrd.open_workbook(file_contents=archivo.read())
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                f"No se pudo leer el archivo -- verifica que sea el reporte de Deudores de Academic+ ({e}).",
            )
            return redirect('importar_cartera_vencida')
 
        deudores_parseados = _parsear_deudores(wb)
        if not deudores_parseados:
            messages.warning(request, "El archivo no tenía saldos vencidos para importar.")
            return redirect('importar_cartera_vencida')
 
        with transaction.atomic():
            CarteraVencida.objects.filter(empresa=perfil.empresa, fecha_corte=fecha_corte).delete()
 
            nuevos = []
            for d in deudores_parseados:
                concepto_upper = d['concepto'].upper()
                if 'COLEGIATURA' in concepto_upper:
                    categoria = 'colegiatura'
                elif 'INSCRIP' in concepto_upper:
                    categoria = 'inscripcion'
                else:
                    categoria = 'otro'
 
                nuevos.append(CarteraVencida(
                    empresa=perfil.empresa,
                    fecha_corte=fecha_corte,
                    matricula=d['matricula'],
                    nombre_alumno=d['nombre'],
                    grupo=d['grupo'],
                    concepto=d['concepto'],
                    categoria=categoria,
                    monto=Decimal(str(d['monto'])),
                ))
            CarteraVencida.objects.bulk_create(nuevos)
 
        total_importado = sum(d['monto'] for d in deudores_parseados)
        messages.success(
            request,
            f"Cartera vencida al corte {fecha_corte.strftime('%d/%m/%Y')} actualizada -- "
            f"{len(nuevos)} concepto(s), total ${total_importado:,.2f}.",
        )
        return redirect('importar_cartera_vencida')
 
    ultima_fecha = (
        CarteraVencida.objects.filter(empresa=perfil.empresa)
        .order_by('-fecha_corte').values_list('fecha_corte', flat=True).first()
    )

    resumen = CarteraVencida.objects.filter(empresa=perfil.empresa, fecha_corte=ultima_fecha).aggregate(
        total=Sum('monto'),
    ) if ultima_fecha else {'total': None}
    total_cartera = resumen['total'] or Decimal('0')  # noqa: FURB157
    alumnos_deudores = (
        CarteraVencida.objects.filter(empresa=perfil.empresa, fecha_corte=ultima_fecha)
        .values('matricula').distinct().count()
    ) if ultima_fecha else 0

    fechas_disponibles = list(
        CarteraVencida.objects.filter(empresa=perfil.empresa)
        .values_list('fecha_corte', flat=True).distinct().order_by('-fecha_corte')
    )

    return render(request, 'escuelas/importar_cartera_vencida.html', {
        'total_cartera': total_cartera,
        'alumnos_deudores': alumnos_deudores,
        'ultima_fecha': ultima_fecha,
        'fechas_disponibles': fechas_disponibles,
        'hoy': date.today(),  # noqa: DTZ011
    })




#### Dashboard de inicio de escuela ####
@login_required
@requiere_membresia_activa_escuela
def dashboard_inicio_escuela(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
        return redirect('dashboard_inicio')
 
    empresa = perfil.empresa
    hoy = date.today()  # noqa: DTZ011
 
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
 
    ingresos_mes_actual = _ingresos_base(empresa).filter(
        fecha__year=anio_sel, fecha__month=mes_sel,
    ).aggregate(total=Sum('monto'))['total'] or 0
 
    ingresos_acumulados = _ingresos_base(empresa).aggregate(total=Sum('monto'))['total'] or 0
 
    ingresos_por_categoria = (
        _ingresos_base(empresa).filter(fecha__year=anio_sel, fecha__month=mes_sel)
        .values('categoria')
        .annotate(total=Sum('monto'))
        .order_by('-total')
    )
 
    gastos_del_periodo = Gasto.objects.filter(
        empresa=empresa, fecha__year=anio_sel, fecha__month=mes_sel,
    ).exclude(estatus='cancelada')

    gastos_por_categoria = (
        gastos_del_periodo
        .values('tipo_gasto__nombre')
        .annotate(total=Sum('monto'))
        .order_by('-total')
    )
    total_gastos_mes = gastos_del_periodo.aggregate(total=Sum('monto'))['total'] or Decimal('0')  # noqa: FURB157
 
    # Pagos con tarjeta del portal web. Ahora salen del Detalle de Pagos, al 100%.
    # La comision es solo una ESTIMACION de referencia (debito/credito/amex segun
    # COMISION_REFERENCIA): la comision real la registra el usuario como gasto.
    ingreso_bruto_plataforma = Decimal('0')  # noqa: FURB157
    comision_plataforma = Decimal('0')  # noqa: FURB157
    portal_por_forma = (
        IngresoEscuela.objects.filter(
            empresa=empresa, fecha__year=anio_sel, fecha__month=mes_sel,
            forma_pago__icontains='portal web',
        ).exclude(origen='fiserv')
        .values('forma_pago').annotate(total=Sum('monto'))
    )
    for fila in portal_por_forma:
        total_forma = fila['total'] or Decimal('0')  # noqa: FURB157
        ingreso_bruto_plataforma += total_forma
        pct = COMISION_REFERENCIA.get(tipo_tarjeta_merchant(fila['forma_pago']))
        if pct:
            comision_plataforma += (total_forma * pct / Decimal('100')).quantize(Decimal('0.01'))  # noqa: FURB157

    if not ingreso_bruto_plataforma:
        # Meses anteriores al nuevo importador: se conservan los datos historicos 'fiserv'.
        resumen_fiserv_mes = IngresoEscuela.objects.filter(
            empresa=empresa, origen='fiserv', fecha__year=anio_sel, fecha__month=mes_sel,
        ).aggregate(bruto=Sum('monto'), comision=Sum('comision'))
        ingreso_bruto_plataforma = resumen_fiserv_mes['bruto'] or Decimal('0')  # noqa: FURB157
        comision_plataforma = resumen_fiserv_mes['comision'] or Decimal('0')  # noqa: FURB157
    ingreso_neto_plataforma = ingreso_bruto_plataforma - comision_plataforma
 
    # --- Banco vs efectivo del periodo ---
    ingresos_periodo_qs = _ingresos_base(empresa).filter(fecha__year=anio_sel, fecha__month=mes_sel)
    ingresos_efectivo_mes = ingresos_periodo_qs.filter(es_efectivo=True).aggregate(t=Sum('monto'))['t'] or Decimal('0')  # noqa: FURB157
    ingresos_banco_mes = ingresos_periodo_qs.filter(es_efectivo=False).aggregate(t=Sum('monto'))['t'] or Decimal('0')  # noqa: FURB157
    resultado_mes = ingresos_mes_actual - total_gastos_mes

    # --- Saldos de bancos al cierre del mes seleccionado ---
    if mes_sel == 12:  
        anio_sig, mes_sig = anio_sel + 1, 1
    else:
        anio_sig, mes_sig = anio_sel, mes_sel + 1
    saldos_bancos = []
    saldo_bancos_total = Decimal('0')  # noqa: FURB157
    for cuenta in CuentaBancaria.objects.filter(empresa=empresa, activa=True).order_by('banco'):
        try:
            saldo_cuenta = calcular_saldo_acumulado_hasta(cuenta, anio_sig, mes_sig)
        except Exception:  
            logger.exception('No se pudo calcular el saldo de la cuenta %s', cuenta.pk)
            continue
        saldos_bancos.append({'cuenta': cuenta, 'saldo': saldo_cuenta})
        saldo_bancos_total += saldo_cuenta

    # --- Caja chica (efectivo cobrado + fondeos normales) ---
    fondeos_qs = FondeoCajaChica.objects.filter(empresa=empresa)
    saldo_caja_efectivo = fondeos_qs.filter(origen='cobros_efectivo').aggregate(t=Sum('saldo'))['t'] or Decimal('0')  # noqa: FURB157
    saldo_caja_otros = fondeos_qs.exclude(origen='cobros_efectivo').aggregate(t=Sum('saldo'))['t'] or Decimal('0')  # noqa: FURB157

    ultimos_lotes = LoteImportacionIngresos.objects.filter(empresa=empresa).order_by('-fecha_importacion')[:3]

    total_alumnos_activos = Alumno.objects.filter(empresa=empresa, activo=True).count()
    alumnos_preescolar = Alumno.objects.filter(empresa=empresa, activo=True, nivel='preescolar').count()
    alumnos_primaria = Alumno.objects.filter(empresa=empresa, activo=True, nivel='primaria').count()
    alumnos_nuevos_mes = Alumno.objects.filter(
        empresa=empresa, fecha_alta__year=anio_sel, fecha_alta__month=mes_sel,
    ).count()
    bajas_recientes_count = Alumno.objects.filter(
        empresa=empresa, activo=False,
        fecha_baja_detectada__year=anio_sel, fecha_baja_detectada__month=mes_sel,
    ).count()
 
    ultima_fecha_cartera = (
        CarteraVencida.objects.filter(empresa=empresa)
        .order_by('-fecha_corte').values_list('fecha_corte', flat=True).first()
    )
    cartera_vencida_qs = CarteraVencida.objects.filter(
        empresa=empresa, fecha_corte=ultima_fecha_cartera,
    ) if ultima_fecha_cartera else CarteraVencida.objects.none()
    cartera_vencida_total = cartera_vencida_qs.aggregate(total=Sum('monto'))['total'] or Decimal('0')  # noqa: FURB157
    cartera_vencida_alumnos = cartera_vencida_qs.values('matricula').distinct().count()
 
    primer_registro = _ingresos_base(empresa).order_by('fecha').first()
    anio_min = primer_registro.fecha.year if primer_registro else hoy.year
    anios_disponibles = list(range(anio_min, hoy.year + 1))
 
    rango_6_meses = _ultimos_n_meses(fecha_referencia, n=6)
    labels_grafico = [f"{MESES_ABREVIADOS[m]} {a}" for a, m in rango_6_meses]
    fecha_inicio_rango = date(rango_6_meses[0][0], rango_6_meses[0][1], 1)
 
    ingresos_qs = (
        _ingresos_base(empresa).filter(fecha__gte=fecha_inicio_rango)
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
        'hoy': hoy,
        'ingresos_mes_actual': ingresos_mes_actual,
        'ingresos_acumulados': ingresos_acumulados,
        'ingresos_por_categoria': ingresos_por_categoria,
        'gastos_por_categoria': gastos_por_categoria,
        'total_gastos_mes': total_gastos_mes,
        'ingreso_bruto_plataforma': ingreso_bruto_plataforma,
        'comision_plataforma': comision_plataforma,
        'ingreso_neto_plataforma': ingreso_neto_plataforma,
        'ingresos_efectivo_mes': ingresos_efectivo_mes,
        'ingresos_banco_mes': ingresos_banco_mes,
        'resultado_mes': resultado_mes,
        'saldos_bancos': saldos_bancos,
        'saldo_bancos_total': saldo_bancos_total,
        'saldo_caja_efectivo': saldo_caja_efectivo,
        'saldo_caja_otros': saldo_caja_otros,
        'ultimos_lotes': ultimos_lotes,
        'total_alumnos_activos': total_alumnos_activos,
        'alumnos_preescolar': alumnos_preescolar,
        'alumnos_primaria': alumnos_primaria,
        'alumnos_nuevos_mes': alumnos_nuevos_mes,
        'bajas_recientes_count': bajas_recientes_count,
        'cartera_vencida_total': cartera_vencida_total,
        'cartera_vencida_alumnos': cartera_vencida_alumnos,
        'labels_grafico': labels_grafico,
        'datos_ingresos': datos_ingresos,
        'datos_gastos': datos_gastos,
    })

  


## Dashboard de admisiones de escuela ##
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



@login_required
@requiere_membresia_activa_escuela
def matriz_presupuesto_ingresos_escuela(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
        return redirect('dashboard_inicio')
    empresa = perfil.empresa
 
    anios_con_presupuesto = list(
        PresupuestoIngresoEscuela.objects.filter(empresa=empresa)
        .values_list('anio', flat=True).distinct().order_by('anio')
    )
 
    try:
        anio = int(request.GET.get('anio', 0))
    except (TypeError, ValueError):
        anio = 0
    if anio not in anios_con_presupuesto:
        anio = anios_con_presupuesto[-1] if anios_con_presupuesto else now().year
 
    meses = list(range(1, 13))
    meses_nombres = [month_name[m].capitalize() for m in meses]
    categorias = IngresoEscuela.CATEGORIA_CHOICES
 
    if request.method == 'POST':
        cambios = []
        for categoria, _ in categorias:
            for mes in meses:
                key = f"presupuesto_{categoria}_{mes}"
                monto_raw = request.POST.get(key)
                if monto_raw is not None:
                    try:
                        monto = Decimal(monto_raw or '0')
                    except Exception:  # noqa: BLE001
                        monto = Decimal('0')  # noqa: FURB157
                    cambios.append({'categoria': categoria, 'mes': mes, 'monto': monto})
 
        existentes = PresupuestoIngresoEscuela.objects.filter(empresa=empresa, anio=anio)
        existentes_dict = {(p.categoria, p.mes): p for p in existentes}
 
        nuevos = []
        actualizados = []
        for c in cambios:
            key = (c['categoria'], c['mes'])
            obj = existentes_dict.get(key)
            if obj:
                if obj.monto_presupuestado != c['monto']:
                    obj.monto_presupuestado = c['monto']
                    actualizados.append(obj)
            else:
                nuevos.append(PresupuestoIngresoEscuela(
                    empresa=empresa, anio=anio, mes=c['mes'],
                    categoria=c['categoria'], monto_presupuestado=c['monto'],
                ))
 
        if actualizados:
            PresupuestoIngresoEscuela.objects.bulk_update(actualizados, ['monto_presupuestado'])
        if nuevos:
            PresupuestoIngresoEscuela.objects.bulk_create(nuevos)
 
        messages.success(request, "Presupuesto de ingresos actualizado.")
        return redirect(request.path + f"?anio={anio}")
 
    presupuestos_qs = (
        PresupuestoIngresoEscuela.objects.filter(empresa=empresa, anio=anio)
        .values('categoria', 'mes')
        .annotate(monto=Sum('monto_presupuestado'))
    )
    presup_dict = {c: {m: Decimal('0') for m in meses} for c, _ in categorias}  # noqa: FURB157
    for p in presupuestos_qs:
        presup_dict[p['categoria']][p['mes']] = p['monto'] or Decimal('0')  # noqa: FURB157
 
    real_dict = {c: {m: Decimal('0') for m in meses} for c, _ in categorias}  # noqa: FURB157
    reales_por_mes_qs = (
        _ingresos_base(empresa).filter(fecha__year=anio)
        .values('categoria', 'fecha__month')
        .annotate(monto=Sum('monto'))
    )
    for r in reales_por_mes_qs:
        cat = r['categoria']
        mes = r['fecha__month']
        if cat in real_dict:
            real_dict[cat][mes] = r['monto'] or Decimal('0')  # noqa: FURB157
 
    subtotales_presup = {c: [presup_dict[c][m] for m in meses] for c, _ in categorias}
    subtotales_real = {c: [real_dict[c][m] for m in meses] for c, _ in categorias}
 
    totales_mes_presup = [sum(subtotales_presup[c][i] for c, _ in categorias) for i in range(len(meses))]
    totales_mes_real = [sum(subtotales_real[c][i] for c, _ in categorias) for i in range(len(meses))]
 
    totales_por_categoria_presup = {c: sum(subtotales_presup[c]) for c, _ in categorias}
    totales_por_categoria_real = {c: sum(subtotales_real[c]) for c, _ in categorias}

    diferencias_por_categoria = {
        c: totales_por_categoria_real[c] - totales_por_categoria_presup[c]
        for c, _ in categorias
    }
 
    return render(request, 'escuelas/matriz_presupuesto_ingresos.html', {
        'categorias': categorias,
        'meses': meses,
        'meses_nombres': meses_nombres,
        'presup_dict': presup_dict,
        'real_dict': real_dict,
        'anio': anio,
        'anios': anios_con_presupuesto,
        'totales_mes_presup': totales_mes_presup,
        'totales_mes_real': totales_mes_real,
        'totales_por_categoria_presup': totales_por_categoria_presup,
        'totales_por_categoria_real': totales_por_categoria_real,
        'mes_actual_num': now().month,
        'anio_actual': now().year,
        'diferencias_por_categoria': diferencias_por_categoria,
    })


@login_required
@requiere_membresia_activa_escuela
def estado_resultados_escuela(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
        return redirect('dashboard_inicio')
    empresa = perfil.empresa
 
    hoy = datetime.date.today()  # noqa: DTZ011
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    mes = request.GET.get('mes')
    anio = request.GET.get('anio')
    periodo = request.GET.get('periodo')
 
    meses_anios_ingresos = (
        _ingresos_base(empresa)
        .dates('fecha', 'month')
    )
    meses_anios_gastos = (
        Gasto.objects.filter(empresa=empresa)
        .dates('fecha', 'month')
    )
    meses_anios_set = {(d.month, d.year) for d in list(meses_anios_ingresos) + list(meses_anios_gastos)}
    meses_unicos = sorted({m for m, _ in meses_anios_set})
    anios_unicos = sorted({a for _, a in meses_anios_set})
 
    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = 'periodo_actual'
 
    if periodo == 'mes_actual':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (hoy.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        mes = hoy.month
        anio = hoy.year
    elif periodo == 'periodo_actual':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy
        mes = ''
        anio = ''
    elif mes and anio:
        try:
            mes = int(mes)
            anio = int(anio)
            fecha_inicio = datetime.date(anio, mes, 1)
            fecha_fin = (
                datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)
                if mes < 12 else datetime.date(anio, 12, 31)
            )
        except (TypeError, ValueError):
            fecha_inicio = None
            fecha_fin = None
    elif fecha_inicio and fecha_fin:
        pass
    else:
        fecha_inicio = None
        fecha_fin = None
 
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d').date()  # noqa: DTZ007
        except ValueError:
            fecha_inicio = None
    if isinstance(fecha_fin, str):
        try:
            fecha_fin = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d').date()  # noqa: DTZ007
        except ValueError:
            fecha_fin = None
 
    try:
        locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, 'C')
 
    mes_letra = ''
    if fecha_inicio and fecha_fin:
        if fecha_inicio == fecha_fin.replace(day=1) and fecha_inicio.month == fecha_fin.month:
            mes_letra = fecha_inicio.strftime('%B %Y').capitalize()
        else:
            mes_letra = f"{fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
 
    ingresos_qs = _ingresos_base(empresa)
    gastos_qs = Gasto.objects.filter(empresa=empresa).exclude(estatus='cancelada')
    if fecha_inicio:
        ingresos_qs = ingresos_qs.filter(fecha__gte=fecha_inicio)
        gastos_qs = gastos_qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        ingresos_qs = ingresos_qs.filter(fecha__lte=fecha_fin)
        gastos_qs = gastos_qs.filter(fecha__lte=fecha_fin)
 
    ingresos_por_categoria = OrderedDict()
    for x in ingresos_qs.values('categoria').annotate(total=Sum('monto')).order_by('-total'):
        etiqueta = dict(IngresoEscuela.CATEGORIA_CHOICES).get(x['categoria'], x['categoria'])
        ingresos_por_categoria[etiqueta] = float(x['total'] or 0)
    total_ingresos = float(sum(ingresos_por_categoria.values()))
 
    gastos_por_categoria = OrderedDict()
    for x in gastos_qs.values('tipo_gasto__nombre').annotate(total=Sum('monto')).order_by('-total'):
        etiqueta = x['tipo_gasto__nombre'] or 'Sin categoría'
        gastos_por_categoria[etiqueta] = float(x['total'] or 0)
    total_gastos = float(sum(gastos_por_categoria.values()))
 
    resultado_neto = total_ingresos - total_gastos
 
    return render(request, 'escuelas/estado_resultados.html', {
        'empresa': empresa,
        'ingresos_por_categoria': ingresos_por_categoria,
        'gastos_por_categoria': gastos_por_categoria,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'resultado_neto': resultado_neto,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d') if fecha_inicio else '',
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d') if fecha_fin else '',
        'mes': str(mes or ''),
        'anio': str(anio or ''),
        'periodo': periodo,
        'meses_unicos': meses_unicos,
        'anios_unicos': anios_unicos,
        'mes_letra': mes_letra,
    })



@login_required
@requiere_membresia_activa_escuela
def reporte_cartera_vencida_comparativo(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa or perfil.empresa.segmento != 'escuela':
        return redirect('dashboard_inicio')
    empresa = perfil.empresa
 
    fechas_corte = list(
        CarteraVencida.objects.filter(empresa=empresa)
        .values_list('fecha_corte', flat=True).distinct().order_by('fecha_corte')
    )
    categorias = CarteraVencida.CATEGORIA_CHOICES
 
    datos_qs = (
        CarteraVencida.objects.filter(empresa=empresa)
        .values('fecha_corte', 'categoria')
        .annotate(total=Sum('monto'))
    )
    matriz = {c: {f: Decimal('0') for f in fechas_corte} for c, _ in categorias}
    for d in datos_qs:
        if d['categoria'] in matriz:
            matriz[d['categoria']][d['fecha_corte']] = d['total'] or Decimal('0')
 
    totales_por_fecha = [
        sum(matriz[c][f] for c, _ in categorias) for f in fechas_corte
    ]
 
    variaciones = [None]
    for i in range(1, len(totales_por_fecha)):
        variaciones.append(totales_por_fecha[i] - totales_por_fecha[i - 1])
 
    labels_grafico = [f.strftime('%d/%m/%y') for f in fechas_corte]
 
    return render(request, 'escuelas/reporte_cartera_comparativo.html', {
        'fechas_corte': fechas_corte,
        'labels_grafico': labels_grafico,
        'categorias': categorias,
        'matriz': matriz,
        'totales_por_fecha': totales_por_fecha,
        'variaciones': variaciones,
        'totales_por_fecha_float': [float(t) for t in totales_por_fecha],
    })




## Membresía vencida de escuela ##
@login_required
def membresia_vencida_escuela(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    return render(request, 'escuelas/membresia_vencida.html', {
        'perfil': perfil,
        'config': ConfiguracionMembresia.obtener(),
    })


# Vista -- no necesita lógica, solo renderiza el template.
#vista para la landing page de Gesac Campus
class LandingGesacCampusView(TemplateView):
    template_name = "escuelas/landing_gesac_campus.html"




### Webhook HubSpot Admisiones######

logger = logging.getLogger(__name__)


MAPEO_ETAPAS_HUBSPOT = {
    "1439855671": "prospecto",
    "1439855672": "contacto",
    "1439855673": "visita_agendada",
    "1439855674": "visita_realizada",
    "1439855675": "solicitud",
    "1439855676": "inscrito",
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
    etapa_id_str = str(etapa_id_hubspot).strip() if etapa_id_hubspot is not None else ''
    etapa = MAPEO_ETAPAS_HUBSPOT.get(etapa_id_str, 'prospecto')
    if etapa_id_str and etapa_id_str not in MAPEO_ETAPAS_HUBSPOT:
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