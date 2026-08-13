import datetime
from decimal import Decimal

from django.db.models import Sum

from caja_chica.models import FondeoCajaChica
from conciliaciones.models import SaldoCuentaPeriodo
from facturacion.models import CobroOtrosIngresos, Pago
from gastos.models import PagoGasto
from traspasos.models import TraspasoBancario


def calcular_saldo_cuenta_periodo(cuenta, anio, mes):
    pagos = Pago.objects.filter(
        cuenta_bancaria=cuenta,
        fecha_pago__year=anio,
        fecha_pago__month=mes
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    cobros_oi = CobroOtrosIngresos.objects.filter(
        cuenta_bancaria=cuenta,
        fecha_cobro__year=anio,
        fecha_cobro__month=mes
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    pagos_gastos = PagoGasto.objects.filter(
        cuenta_bancaria=cuenta,
        fecha_pago__year=anio,
        fecha_pago__month=mes
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    fondeos = FondeoCajaChica.objects.filter(
        cuenta_bancaria=cuenta,
        fecha__year=anio,
        fecha__month=mes
    ).aggregate(total=Sum('importe_cheque'))['total'] or Decimal('0')

    traspasos_salida = TraspasoBancario.objects.filter(
        cuenta_origen=cuenta,
        fecha__year=anio,
        fecha__month=mes,
        estado='completado'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    traspasos_entrada = TraspasoBancario.objects.filter(
        cuenta_destino=cuenta,
        fecha__year=anio,
        fecha__month=mes,
        estado='completado'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    total_ingresos = pagos + cobros_oi + traspasos_entrada
    total_egresos = pagos_gastos + fondeos + traspasos_salida

    return {
        'pagos': pagos,
        'cobros_oi': cobros_oi,
        'traspasos_entrada': traspasos_entrada,
        'total_ingresos': total_ingresos,
        'pagos_gastos': pagos_gastos,
        'fondeos': fondeos,
        'traspasos_salida': traspasos_salida,
        'total_egresos': total_egresos,
        'movimiento_neto': total_ingresos - total_egresos,
    }


def calcular_saldo_acumulado_hasta(cuenta, anio, mes):

    fecha_limite = datetime.date(anio, mes, 1)

    pagos = Pago.objects.filter(
        cuenta_bancaria=cuenta,
        fecha_pago__lt=fecha_limite
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    cobros_oi = CobroOtrosIngresos.objects.filter(
        cuenta_bancaria=cuenta,
        fecha_cobro__lt=fecha_limite
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    pagos_gastos = PagoGasto.objects.filter(
        cuenta_bancaria=cuenta,
        fecha_pago__lt=fecha_limite
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    fondeos = FondeoCajaChica.objects.filter(
        cuenta_bancaria=cuenta,
        fecha__lt=fecha_limite
    ).aggregate(total=Sum('importe_cheque'))['total'] or Decimal('0')

    traspasos_salida = TraspasoBancario.objects.filter(
        cuenta_origen=cuenta,
        fecha__lt=fecha_limite,
        estado='completado'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    traspasos_entrada = TraspasoBancario.objects.filter(
        cuenta_destino=cuenta,
        fecha__lt=fecha_limite,
        estado='completado'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    total_ingresos = pagos + cobros_oi + traspasos_entrada
    total_egresos = pagos_gastos + fondeos + traspasos_salida

    return (cuenta.saldo_inicial or Decimal('0')) + total_ingresos - total_egresos


def get_o_crear_periodo(cuenta, empresa, anio, mes):
    periodo_existente = SaldoCuentaPeriodo.objects.filter(
        cuenta=cuenta, anio=anio, mes=mes
    ).first()

    if periodo_existente:
        movimientos = calcular_saldo_cuenta_periodo(cuenta, anio, mes)
        if not periodo_existente.cerrado:
            periodo_existente.saldo_calculado = periodo_existente.saldo_inicial + movimientos['movimiento_neto']
            periodo_existente.save()
        return periodo_existente, movimientos

    mes_anterior = mes - 1
    anio_anterior = anio
    if mes_anterior == 0:
        mes_anterior = 12
        anio_anterior = anio - 1

    periodo_anterior_cerrado = SaldoCuentaPeriodo.objects.filter(
        cuenta=cuenta,
        anio=anio_anterior,
        mes=mes_anterior,
        cerrado=True
    ).first()

    if periodo_anterior_cerrado:
        saldo_inicial = periodo_anterior_cerrado.saldo_final
    else:
        saldo_inicial = calcular_saldo_acumulado_hasta(cuenta, anio, mes)

    movimientos = calcular_saldo_cuenta_periodo(cuenta, anio, mes)
    saldo_calculado = saldo_inicial + movimientos['movimiento_neto']

    periodo = SaldoCuentaPeriodo.objects.create(
        cuenta=cuenta,
        empresa=empresa,
        anio=anio,
        mes=mes,
        saldo_inicial=saldo_inicial,
        saldo_calculado=saldo_calculado,
    )

    return periodo, movimientos


def validar_periodo_abierto(cuenta, fecha, user=None):
   
    if not fecha:
        return True, None
    
    hoy = datetime.date.today()  # noqa: DTZ011

    # Superusuario puede registrar en años anteriores
    #if not (user and user.is_superuser):
    # Política de seguridad: no se puede registrar en años anteriores al actual
    if not (user and user.is_superuser):  # noqa: SIM102
        if fecha.year < hoy.year:
            return False, (
                f"No se pueden registrar movimientos con fecha del año {fecha.year}. "
                f"Solo se permiten movimientos del año {hoy.year} en adelante."
            )

    # Política adicional: no se puede registrar con fecha futura
    if fecha > hoy:
        return False, (
            f"No se pueden registrar movimientos con fecha futura ({fecha.strftime('%d/%m/%Y')}). "
            f"La fecha máxima permitida es hoy ({hoy.strftime('%d/%m/%Y')})."
    )

    # Verificar si el período está cerrado
    # Verificar si el período está cerrado -- SOLO bloquea si además es de un año ANTERIOR.
    # Un período cerrado del año actual ya no bloquea nada (la regla de "año actual" de arriba basta).
    if cuenta and fecha.year < hoy.year:
        periodo = SaldoCuentaPeriodo.objects.filter(
            cuenta=cuenta,
            anio=fecha.year,
            mes=fecha.month,
            cerrado=True
        ).first()

        if periodo:
            return False, (
                f"El período {periodo.nombre_mes()} {periodo.anio} ya está cerrado. "
                f"No se pueden registrar movimientos en períodos cerrados."
            )

    return True, None


def _saldo_inversion_a_fecha(cuenta, fecha_corte):
    """Saldo de una cuenta de inversión reconstruido a una fecha de corte
    exacta, sumando incrementos/rendimientos y restando retiros."""
    entrantes = TraspasoBancario.objects.filter(
        cuenta_destino=cuenta, es_inversion=True, estado='completado', fecha__lte=fecha_corte
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    salientes = TraspasoBancario.objects.filter(
        cuenta_origen=cuenta, es_inversion=True, estado='completado', fecha__lte=fecha_corte
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    rendimientos = CobroOtrosIngresos.objects.filter(
        cuenta_bancaria=cuenta, factura__tipo_ingreso__nombre='Rendimientos Financieros', fecha_cobro__lte=fecha_corte
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    return (cuenta.saldo_inicial or Decimal('0')) + entrantes + rendimientos - salientes


def _rendimiento_en_rango(cuenta, fecha_inicio, fecha_fin):
    """Suma de rendimientos generados en un rango de fechas (no acumulado)."""
    return CobroOtrosIngresos.objects.filter(
        cuenta_bancaria=cuenta, factura__tipo_ingreso__nombre='Rendimientos Financieros',
        fecha_cobro__gte=fecha_inicio, fecha_cobro__lte=fecha_fin
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')


def _variacion(actual, anterior):
    """Devuelve (diferencia_absoluta, porcentaje) -- porcentaje None si anterior es 0."""
    diferencia = actual - anterior
    if anterior and anterior != 0:
        porcentaje = round(float(diferencia) / float(anterior) * 100, 1)
    else:
        porcentaje = None
    return diferencia, porcentaje