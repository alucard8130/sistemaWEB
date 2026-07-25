from datetime import date
from django.shortcuts import render
from .models import Factura, FacturaOtrosIngresos
from decimal import Decimal
from django.db.models import Sum, Q,F, ExpressionWrapper, Value, DecimalField
from django.db.models.functions import Coalesce


def debe_mostrar_recordatorio_facturacion(empresa):
    hoy = date.today()
    if hoy.day > 2 and empresa:
        existe = Factura.objects.filter(
            empresa=empresa,
            fecha_emision__year=hoy.year,
            fecha_emision__month=hoy.month
        ).exists()
        return not existe
    return False


"""Cálculo de cartera vencida con reconstrucción histórica por fecha de corte."""
def _saldo_vencido_a_fecha(modelo, campo_relacion_pagos, campo_fecha_pago, empresa, fecha_corte):
    facturas = modelo.objects.filter(
        empresa=empresa, activo=True, fecha_vencimiento__lte=fecha_corte,
    ).exclude(estatus='cancelada').annotate(
        pagado_a_corte=Sum(
            f'{campo_relacion_pagos}__monto',
            filter=Q(**{
                f'{campo_relacion_pagos}__{campo_fecha_pago}__isnull': False,
                f'{campo_relacion_pagos}__{campo_fecha_pago}__lte': fecha_corte,
            })
        )
    ).select_related('cliente')

    total = Decimal('0')
    detalle = []

    for factura in facturas:
        pagado = factura.pagado_a_corte or Decimal('0')
        saldo = factura.monto - pagado

        total += saldo  # incluye negativos (sobrepagos), igual que el dashboard

        if saldo > 0:
            detalle.append({
                'factura': factura,
                'cliente': factura.cliente,
                'saldo': saldo,
            })

    return total, detalle


def calcular_cartera_vencida(empresa, fecha_corte, incluir_cuotas=True, incluir_otros=True):
    """
    Calcula la cartera vencida total de la empresa a una fecha de corte,
    combinando Factura (cuotas) y/o FacturaOtrosIngresos según se pida.

    Devuelve dict: {
        'total': Decimal,
        'detalle': list combinado de ambos tipos,
        'por_cliente': dict {cliente_id: {'cliente': ..., 'saldo': Decimal}}
    }
    """
    total = Decimal('0')
    detalle = []

    if incluir_cuotas:
        total_cuotas, detalle_cuotas = _saldo_vencido_a_fecha(
            Factura, 'pagos', 'fecha_pago', empresa, fecha_corte
        )
        total += total_cuotas
        detalle.extend(detalle_cuotas)

    if incluir_otros:
        total_otros, detalle_otros = _saldo_vencido_a_fecha(
            FacturaOtrosIngresos, 'cobros', 'fecha_cobro', empresa, fecha_corte
        )
        total += total_otros
        detalle.extend(detalle_otros)

    # Agrupar por cliente para el top de deudores
    por_cliente = {}
    for item in detalle:
        cid = item['cliente'].id
        if cid not in por_cliente:
            por_cliente[cid] = {'cliente': item['cliente'], 'saldo': Decimal('0')}
        por_cliente[cid]['saldo'] += item['saldo']

    return {
        'total': total,
        'detalle': detalle,
        'por_cliente': por_cliente,
    }


def variacion(actual, anterior):
    """Devuelve (diferencia_absoluta, porcentaje) -- porcentaje None si anterior es 0."""
    diferencia = actual - anterior
    if anterior and anterior != 0:
        porcentaje = round(float(diferencia) / float(anterior) * 100, 1)
    else:
        porcentaje = None
    return diferencia, porcentaje


def _total_vencido_a_fecha_rapido(modelo, campo_relacion_pagos, campo_fecha_pago, empresa, fecha_corte):
    """Versión ligera: solo el TOTAL agregado en SQL, sin armar detalle por
    cliente. Pensada para calcular muchos cortes rápido (tendencia anual)."""
    resultado = modelo.objects.filter(
        empresa=empresa, activo=True, fecha_vencimiento__lte=fecha_corte,
    ).exclude(estatus='cancelada').annotate(
        pagado_a_corte=Coalesce(
            Sum(
                f'{campo_relacion_pagos}__monto',
                filter=Q(**{
                    f'{campo_relacion_pagos}__{campo_fecha_pago}__isnull': False,
                    f'{campo_relacion_pagos}__{campo_fecha_pago}__lte': fecha_corte,
                })
            ),
            Value(Decimal('0'), output_field=DecimalField())
        )
    ).aggregate(
        total=Sum(ExpressionWrapper(F('monto') - F('pagado_a_corte'), output_field=DecimalField()))
    )
    return resultado['total'] or Decimal('0')


def calcular_total_vencida_rapido(empresa, fecha_corte, incluir_cuotas=True, incluir_otros=True):
    total = Decimal('0')
    if incluir_cuotas:
        total += _total_vencido_a_fecha_rapido(Factura, 'pagos', 'fecha_pago', empresa, fecha_corte)
    if incluir_otros:
        total += _total_vencido_a_fecha_rapido(FacturaOtrosIngresos, 'cobros', 'fecha_cobro', empresa, fecha_corte)
    return total