from datetime import date
from django.shortcuts import render

from areas.models import AreaComun
from locales.models import LocalComercial
from .models import Factura, FacturaOtrosIngresos
from decimal import Decimal
from django.db.models import Sum, Q,F, ExpressionWrapper, Value, DecimalField
from django.db.models.functions import Coalesce
import datetime as dt
from django.db.models import Max


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


def generar_facturas_mes(empresa, año, mes, facturar_locales=True, facturar_areas=True):
    """Núcleo reutilizable de la facturación mensual -- usado tanto por la
    vista manual (facturar_mes_actual) como por el comando automático.
    Es idempotente: si una propiedad ya tiene factura del mes, la omite."""
    fecha_factura = dt.date(año, mes, 1)
    facturas_creadas = 0
    facturas_omitidas = 0
    facturas_a_crear = []

    def get_last_num(prefix):
        max_folio = Factura.objects.filter(
            empresa=empresa, folio__startswith=prefix
        ).aggregate(max_f=Max("folio"))["max_f"]
        if max_folio:
            try:
                return int(max_folio.replace(prefix, ""))
            except Exception:
                return 0
        return 0

    if facturar_locales:
        locales = LocalComercial.objects.filter(
            empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=False
        ).select_related("cliente")
        locales_ids = list(locales.values_list("id", flat=True))
        locales_con_factura = set(
            Factura.objects.filter(
                local_id__in=locales_ids, tipo_cuota="mantenimiento",
                estatus__in=["pendiente", "cobrada", "cancelada"],
            ).filter(
                Q(fecha_emision__year=año, fecha_emision__month=mes)
                | Q(fecha_vencimiento__year=año, fecha_vencimiento__month=mes)
            ).values_list("local_id", flat=True)
        )
        last_num_cm = get_last_num("CM-F")
        last_num_dg = get_last_num("DG-F")

        for local in locales:
            if local.id in locales_con_factura:
                facturas_omitidas += 1
            else:
                last_num_cm += 1
                facturas_a_crear.append(Factura(
                    empresa=empresa, cliente=local.cliente, local=local,
                    folio=f"CM-F{last_num_cm:05d}", fecha_emision=fecha_factura,
                    fecha_vencimiento=fecha_factura, monto=local.cuota,
                    tipo_cuota="mantenimiento", estatus="pendiente", observaciones="Cuota mensual",
                ))
                facturas_creadas += 1

        if mes == 1:
            locales_anuales = LocalComercial.objects.filter(
                empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=True
            ).select_related("cliente")
            locales_anuales_ids = list(locales_anuales.values_list("id", flat=True))
            locales_anuales_con_factura = set(
                Factura.objects.filter(
                    local_id__in=locales_anuales_ids, tipo_cuota="mantenimiento",
                    estatus__in=["pendiente", "cobrada", "cancelada"], fecha_emision__year=año,
                ).values_list("local_id", flat=True)
            )
            for local in locales_anuales:
                if local.id not in locales_anuales_con_factura:
                    last_num_cm += 1
                    facturas_a_crear.append(Factura(
                        empresa=empresa, cliente=local.cliente, local=local,
                        folio=f"CM-F{last_num_cm:05d}", fecha_emision=fecha_factura,
                        fecha_vencimiento=fecha_factura, monto=local.cuota,
                        tipo_cuota="mantenimiento", estatus="pendiente", observaciones="Cuota anual",
                    ))
                    facturas_creadas += 1

    if facturar_areas:
        areas = AreaComun.objects.filter(
            empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=False
        ).select_related("cliente")
        areas_ids = list(areas.values_list("id", flat=True))
        areas_con_factura = set(
            Factura.objects.filter(
                area_comun_id__in=areas_ids, tipo_cuota="renta",
                estatus__in=["pendiente", "cobrada", "cancelada"],
            ).filter(
                Q(fecha_emision__year=año, fecha_emision__month=mes)
                | Q(fecha_vencimiento__year=año, fecha_vencimiento__month=mes)
            ).values_list("area_comun_id", flat=True)
        )
        last_num_ac = get_last_num("AC-F")
        last_num_dg = get_last_num("DG-F") if 'last_num_dg' not in dir() else last_num_dg

        for area in areas:
            if area.id in areas_con_factura:
                facturas_omitidas += 1
            else:
                last_num_ac += 1
                facturas_a_crear.append(Factura(
                    empresa=empresa, cliente=area.cliente, area_comun=area,
                    folio=f"AC-F{last_num_ac:05d}", fecha_emision=fecha_factura,
                    fecha_vencimiento=fecha_factura, monto=area.cuota,
                    tipo_cuota="renta", estatus="pendiente", observaciones="Cuota mensual",
                ))
                facturas_creadas += 1

            if area.deposito and area.deposito > 0:
                existe_deposito = Factura.objects.filter(
                    cliente=area.cliente, area_comun=area, tipo_cuota="deposito",
                ).exists()
                if not existe_deposito:
                    last_num_dg += 1
                    facturas_a_crear.append(Factura(
                        empresa=empresa, cliente=area.cliente, area_comun=area,
                        folio=f"DG-F{last_num_dg:05d}", fecha_emision=fecha_factura,
                        fecha_vencimiento=fecha_factura, monto=area.deposito,
                        tipo_cuota="deposito", estatus="pendiente", observaciones="Depósito en garantía",
                    ))

        if mes == 1:
            areas_anuales = AreaComun.objects.filter(
                empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=True
            ).select_related("cliente")
            areas_anuales_ids = list(areas_anuales.values_list("id", flat=True))
            areas_anuales_con_factura = set(
                Factura.objects.filter(
                    area_comun_id__in=areas_anuales_ids, tipo_cuota="renta",
                    estatus__in=["pendiente", "cobrada", "cancelada"], fecha_emision__year=año,
                ).values_list("area_comun_id", flat=True)
            )
            for area in areas_anuales:
                if area.id not in areas_anuales_con_factura:
                    last_num_ac += 1
                    facturas_a_crear.append(Factura(
                        empresa=empresa, cliente=area.cliente, area_comun=area,
                        folio=f"AC-F{last_num_ac:05d}", fecha_emision=fecha_factura,
                        fecha_vencimiento=fecha_factura, monto=area.cuota,
                        tipo_cuota="renta", estatus="pendiente", observaciones="Cuota anual",
                    ))
                    facturas_creadas += 1

    if facturas_a_crear:
        Factura.objects.bulk_create(facturas_a_crear, batch_size=50)

    return facturas_creadas, facturas_omitidas