from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import transaction
from facturacion.models import Factura
from decimal import Decimal

def _siguiente_folio(prefix, empresa):
    last_folio = (
        Factura.objects
        .filter(empresa=empresa, folio__startswith=prefix)
        .order_by('-folio')
        .values_list('folio', flat=True)
        .first()
    )
    if last_folio:
        try:
            last_num = int(last_folio.replace(prefix, ""))
        except Exception:
            last_num = 0
    else:
        last_num = 0
    return f"{prefix}{last_num + 1:05d}"

def generar_facturas_area(area, hasta=None):
    """
    Genera factura de depósito (si area.deposito>0) y facturas de cuota
    desde area.fecha_inicial hasta 'hasta' (o hoy). Devuelve lista de Factura creadas.
    Requiere que `area.cliente` y `area.empresa` estén presentes.
    """
    if not area or not area.empresa or not area.cliente:
        raise ValueError("Area debe tener 'empresa' y 'cliente' asignados.")

    hoy = hasta or date.today()
    if not area.fecha_inicial:
        return []

    facturas_creadas = []

    with transaction.atomic():
        # Depósito en garantía (único)
        if area.deposito and Decimal(area.deposito) > 0:
            existe_deposito = Factura.objects.filter(
                empresa=area.empresa,
                cliente=area.cliente,
                area_comun=area,
                tipo_cuota='deposito'
            ).exists()
            if not existe_deposito:
                folio_dep = _siguiente_folio("DG-F", area.empresa)
                factura_dep = Factura.objects.create(
                    empresa=area.empresa,
                    cliente=area.cliente,
                    area_comun=area,
                    folio=folio_dep,
                    fecha_emision=hoy,
                    fecha_vencimiento=hoy,
                    monto=area.deposito,
                    tipo_cuota='deposito',
                    estatus='pendiente',
                    observaciones='Depósito en garantía'
                )
                facturas_creadas.append(factura_dep)

        # Facturas de renta/cuota: anual o mensual
        if area.es_cuota_anual:
            inicio_ano = area.fecha_inicial.year
            tope_ano = min(hoy.year, area.fecha_fin.year if area.fecha_fin else hoy.year)
            for ano in range(inicio_ano, tope_ano + 1):
                existe_anual = Factura.objects.filter(
                    empresa=area.empresa,
                    cliente=area.cliente,
                    area_comun=area,
                    tipo_cuota='renta',
                    fecha_emision__year=ano,
                    observaciones__icontains='anual'
                ).exists()
                if not existe_anual:
                    folio = _siguiente_folio("AC-F", area.empresa)
                    factura = Factura.objects.create(
                        empresa=area.empresa,
                        cliente=area.cliente,
                        area_comun=area,
                        folio=folio,
                        fecha_emision=date(ano, 1, 1),
                        fecha_vencimiento=date(ano, 1, 1),
                        monto=area.cuota * Decimal('12'),
                        tipo_cuota='renta',
                        estatus='pendiente',
                        observaciones=f"Cuota anual de {area.fecha_inicial.strftime('%B %Y')} a {area.fecha_fin.strftime('%B %Y')}"
                    )
                    facturas_creadas.append(factura)
        else:
            fecha_tope = min(hoy, area.fecha_fin) if area.fecha_fin else hoy
            periodo = date(area.fecha_inicial.year, area.fecha_inicial.month, 1)
            while periodo <= date(fecha_tope.year, fecha_tope.month, 1):
                existe = Factura.objects.filter(
                    empresa=area.empresa,
                    cliente=area.cliente,
                    area_comun=area,
                    tipo_cuota='renta',
                    fecha_emision__year=periodo.year,
                    fecha_emision__month=periodo.month
                ).exists()
                if not existe:
                    folio = _siguiente_folio("AC-F", area.empresa)
                    factura = Factura.objects.create(
                        empresa=area.empresa,
                        cliente=area.cliente,
                        area_comun=area,
                        folio=folio,
                        fecha_emision=periodo,
                        fecha_vencimiento=periodo,
                        monto=area.cuota,
                        tipo_cuota='renta',
                        estatus='pendiente',
                        observaciones=f"Cuota mensual {periodo.strftime('%B %Y')}"
                    )
                    facturas_creadas.append(factura)
                periodo = periodo + relativedelta(months=1)

    return facturas_creadas