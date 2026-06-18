from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db import transaction
from facturacion.models import Factura

def _siguiente_folio(prefix, empresa):
    ultimo = Factura.objects.filter(empresa=empresa, folio__startswith=prefix).order_by('pk').last()
    if not ultimo or not ultimo.folio:
        return f"{prefix}0001"
    num = int(ultimo.folio.replace(prefix, "")) + 1
    return f"{prefix}{num:04d}"

def generar_facturas_local(local, adeudo=None):
    """
    adeudo: dict con keys 'inicio' (date or 'YYYY-MM'/'YYYY-MM-DD' str),
                   'fin' (optional),
                   'importe' (Decimal or str),
                   'descripcion' (optional)
    Si adeudo proporcionado -> crea UNA factura por el adeudo.
    Si no -> crea la factura del mes corriente por local.cuota.
    """
    if not local.cliente or not local.empresa:
        raise ValueError("Local sin cliente o empresa asignada")

    empresa = local.empresa
    hoy = date.today()
    es_anual = getattr(local, 'es_cuota_anual', False)

    # Período siempre es primer día del mes actual
    periodo = hoy.replace(day=1)

    with transaction.atomic():
        if adeudo:
            # parsear fechas y monto
            inicio = adeudo.get('inicio')
            fin = adeudo.get('fin')
            if isinstance(inicio, str):
                try:
                    inicio = datetime.strptime(inicio, "%Y-%m").date().replace(day=1)
                except Exception:
                    try:
                        inicio = datetime.strptime(inicio, "%Y-%m-%d").date()
                    except Exception:
                        raise ValueError("Formato de 'inicio' inválido. Use YYYY-MM o YYYY-MM-DD")
            if isinstance(fin, str):
                try:
                    fin = datetime.strptime(fin, "%Y-%m").date().replace(day=1)
                except Exception:
                    try:
                        fin = datetime.strptime(fin, "%Y-%m-%d").date()
                    except Exception:
                        fin = None

            importe = adeudo.get('importe')
            importe = Decimal(importe) if importe is not None else Decimal('0.00')
            observaciones = adeudo.get('descripcion') or (f"Adeudo {inicio.isoformat()}" + (f" - {fin.isoformat()}" if fin else ""))

            # evitar duplicados: mismo cliente/local, mismo monto y descripcion (o mismo periodo)
            if not Factura.objects.filter(local=local, tipo_cuota='mantenimiento', monto=importe, observaciones=observaciones ).exists():
                folio = _siguiente_folio('CM-F', empresa)
                Factura.objects.create(
                    empresa=empresa,
                    cliente=local.cliente,
                    local=local,
                    tipo_cuota='mantenimiento',
                    folio=folio,
                    fecha_vencimiento=inicio, 
                    fecha_emision=inicio or date.today(),
                    monto=importe,
                    observaciones=observaciones,
                )
        # crear factura del período corriente (mes o año según es_cuota_anual)
        if not Factura.objects.filter(local=local, tipo_cuota='mantenimiento', fecha_emision=periodo).exists():
            folio = _siguiente_folio('CM-F', empresa)
            
            if es_anual:
                monto = Decimal(local.cuota or 0) * 12
                fecha_fin = periodo + relativedelta(months=12)
                observaciones = f"Cuota anual de {periodo.strftime('%B %Y')} a {fecha_fin.strftime('%B %Y')}"
            else:
                monto = Decimal(local.cuota or 0)
                observaciones = f"Cuota mantenimiento {periodo.strftime('%B %Y')}"
            
            Factura.objects.create(
                empresa=empresa,
                cliente=local.cliente,
                local=local,
                tipo_cuota='mantenimiento',
                folio=folio,
                fecha_vencimiento=periodo,
                fecha_emision=periodo,
                monto=monto,
                observaciones=observaciones,
            )

        else:
            # crear factura del período corriente (mes o año según es_cuota_anual)
            if not Factura.objects.filter(local=local, tipo_cuota='mantenimiento', fecha_emision=periodo).exists():
                folio = _siguiente_folio('CM-F', empresa)
                
                if es_anual:
                    monto = Decimal(local.cuota or 0) * 12
                    fecha_fin = periodo + relativedelta(months=12)
                    observaciones = f"Cuota anual de {periodo.strftime('%B %Y')} a {fecha_fin.strftime('%B %Y')}"
                else:
                    monto = Decimal(local.cuota or 0)
                    observaciones = f"Cuota mantenimiento {periodo.strftime('%B %Y')}"
                
                Factura.objects.create(
                    empresa=empresa,
                    cliente=local.cliente,
                    local=local,
                    tipo_cuota='mantenimiento',
                    folio=folio,
                    fecha_vencimiento=periodo,
                    fecha_emision=periodo,
                    monto=monto,
                    observaciones=observaciones,
            )