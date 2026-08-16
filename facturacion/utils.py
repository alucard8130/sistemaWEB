import datetime as dt
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Max, Q, Sum, Value
from django.db.models.functions import Coalesce

from areas.models import AreaComun
from locales.models import LocalComercial

from .models import (
    IVA_TASA,
    Factura,
    FacturaOtrosIngresos,
    GrupoFacturacion,
    Pago,
    PoolVacancia,
    SaldoAFavor,
)


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


# ============================================================
# Helper -- aplicar saldos a favor a una factura recién creada.

def aplicar_saldos_a_favor(factura):
    """
    Revisa si el cliente de esta factura tiene algún Saldo a Favor
    disponible que aplique a esta propiedad (o a "cualquier propiedad"
    si el saldo no especifica local/área), y lo consume automáticamente
    -- en orden FIFO (el saldo más antiguo primero) -- hasta que la
    factura quede pagada o se acabe el saldo disponible.

    Se debe llamar UNA VEZ por cada factura recién creada, después de
    que ya tenga folio y pk asignados.
    """
    
    saldo_pendiente_factura = factura.monto
    ya_pagado = factura.pagos.aggregate(t=Sum("monto"))["t"] or Decimal("0")
    saldo_pendiente_factura -= ya_pagado

    if saldo_pendiente_factura <= 0:
        return  # ya está pagada por otro medio, no hay nada que hacer

    # Candidatos: saldos activos de este cliente, que apliquen a ESTA
    # propiedad específica, o que no tengan propiedad especificada
    # (aplican a cualquier propiedad del cliente). FIFO por fecha_registro
    # (ya viene ordenado así por Meta.ordering del modelo).
    saldos_candidatos = SaldoAFavor.objects.filter(
        empresa=factura.empresa, cliente=factura.cliente,
        activo=True, monto_disponible__gt=0,
    )
    if factura.local_id:
        saldos_candidatos = saldos_candidatos.filter(
            Q(local_id=factura.local_id) | Q(local__isnull=True, area_comun__isnull=True)
        )
    elif factura.area_comun_id:
        saldos_candidatos = saldos_candidatos.filter(
            Q(area_comun_id=factura.area_comun_id) | Q(local__isnull=True, area_comun__isnull=True)
        )
    else:
        saldos_candidatos = saldos_candidatos.filter(local__isnull=True, area_comun__isnull=True)

    for saldo in saldos_candidatos:
        if saldo_pendiente_factura <= 0:
            break

        monto_a_aplicar = min(saldo.monto_disponible, saldo_pendiente_factura)

        Pago.objects.create(
            factura=factura,
            fecha_pago=factura.fecha_emision,
            monto=monto_a_aplicar,
            forma_pago="saldo_a_favor",
            observaciones=f"Aplicado automáticamente desde saldo a favor #{saldo.id} "
                           f"(pago adelantado del {saldo.fecha_registro}).",
            identificado=True,
            empresa=factura.empresa,
        )

        saldo.monto_disponible -= monto_a_aplicar
        if saldo.monto_disponible <= 0:
            saldo.monto_disponible = Decimal("0")
            saldo.activo = False
        saldo.save(update_fields=["monto_disponible", "activo"])

        saldo_pendiente_factura -= monto_a_aplicar

    # Si con el/los saldo(s) aplicados la factura quedó cubierta al 100%,
    # márcala como cobrada -- igual que si el cliente hubiera pagado normal.
    if saldo_pendiente_factura <= 0 and factura.estatus == "pendiente":
        factura.estatus = "cobrada"
        factura.save(update_fields=["estatus"])



#####funcion principal de facturación mensual, usada por la vista y el comando

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
        # excluye del ciclo individual a los locales que pertenecen a un grupo
        locales = LocalComercial.objects.filter(
            empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=False,
            grupo_facturacion__isnull=True, cuota__gt=0,
        ).select_related("cliente")
        locales_ids = list(locales.values_list("id", flat=True))
        locales_con_factura = set(
            Factura.objects.filter(
                local_id__in=locales_ids, tipo_cuota="mantenimiento",
                estatus__in=["pendiente", "cobrada"],
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
                # NUEVO -- desglose de IVA calculado explícitamente, porque
                # esta factura va por bulk_create (save() nunca se ejecuta).
                mb, miva = calcular_iva_factura(local.cuota, "mantenimiento")
                facturas_a_crear.append(Factura(
                    empresa=empresa, cliente=local.cliente, local=local,
                    folio=f"CM-F{last_num_cm:05d}", fecha_emision=fecha_factura,
                    fecha_vencimiento=fecha_factura, monto=local.cuota,
                    monto_base=mb, monto_iva=miva,
                    tipo_cuota="mantenimiento", estatus="pendiente", observaciones="Cuota mensual",
                ))
                facturas_creadas += 1

        # bloque de Grupos de Facturación: genera 1 factura consolidada por cada grupo activo
        grupos_activos = GrupoFacturacion.objects.filter(empresa=empresa, activo=True).prefetch_related("locales")
        for grupo in grupos_activos:
            locales_grupo = grupo.locales.filter(activo=True, es_cuota_anual=False)
            if not locales_grupo.exists():
                continue

            ya_facturado_grupo = Factura.objects.filter(
                empresa=empresa, locales_incluidos__in=locales_grupo,
                tipo_cuota="mantenimiento", estatus__in=["pendiente", "cobrada"],
            ).filter(
                Q(fecha_emision__year=año, fecha_emision__month=mes)
                | Q(fecha_vencimiento__year=año, fecha_vencimiento__month=mes)
            ).exists()

            if ya_facturado_grupo:
                facturas_omitidas += 1
                continue

            monto_total = locales_grupo.aggregate(t=Sum("cuota"))["t"] or Decimal("0")
            if monto_total <= 0:
                continue

            last_num_cm += 1
            numeros_locales = ", ".join(l.numero for l in locales_grupo.order_by("numero"))
            factura_grupo = Factura.objects.create(
                empresa=empresa, cliente=grupo.cliente, local=None,
                folio=f"CM-F{last_num_cm:05d}", fecha_emision=fecha_factura,
                fecha_vencimiento=fecha_factura, monto=monto_total,
                tipo_cuota="mantenimiento", estatus="pendiente",
                observaciones=f"Cuota — Grupo '{grupo.nombre}' — Locales: {numeros_locales}",
            )
            factura_grupo.locales_incluidos.set(locales_grupo)
            aplicar_saldos_a_favor(factura_grupo)
            facturas_creadas += 1

        # Pools de Vacancia: factura consolidada al cliente que cubre,
        # sumando SOLO los locales del pool que ACTUALMENTE están sin cliente.
        pools_vacancia = PoolVacancia.objects.filter(
            empresa=empresa, activo=True
        ).select_related("cliente_cobertura")

        for pool in pools_vacancia:
            # Fuente de verdad: status="disponible" (no solo cliente vacío) --
            # así se excluyen locales en remodelación, juicio o venta, que
            # tampoco deben facturarse al pool aunque no tengan cliente.
            locales_vacantes = LocalComercial.objects.filter(
                pool_vacancia=pool, activo=True, status="disponible",
                cliente__isnull=True, cuota__gt=0,
            )
            if not locales_vacantes.exists():
                continue

            ya_facturado_pool = Factura.objects.filter(
                empresa=empresa, pool_vacancia=pool,
                estatus__in=["pendiente", "cobrada"],
            ).filter(
                Q(fecha_emision__year=año, fecha_emision__month=mes)
                | Q(fecha_vencimiento__year=año, fecha_vencimiento__month=mes)
            ).exists()

            if ya_facturado_pool:
                facturas_omitidas += 1
                continue

            monto_total = locales_vacantes.aggregate(t=Sum("cuota"))["t"] or Decimal("0")
            if monto_total <= 0:
                continue

            last_num_cm += 1
            numeros_locales = ", ".join(l.numero for l in locales_vacantes.order_by("numero"))
            factura_vacancia = Factura.objects.create(
                empresa=empresa, cliente=pool.cliente_cobertura, local=None,
                pool_vacancia=pool,
                folio=f"CM-F{last_num_cm:05d}", fecha_emision=fecha_factura,
                fecha_vencimiento=fecha_factura, monto=monto_total,
                tipo_cuota="mantenimiento", estatus="pendiente",
                observaciones=f"Cuota Prop. vacías — Pool '{pool.nombre}' — "
                               f"Prop. vacías este mes: {numeros_locales}",
            )
            factura_vacancia.locales_incluidos.set(locales_vacantes)
            aplicar_saldos_a_favor(factura_vacancia)
            facturas_creadas += 1

        # Cuota anual -- se revisa en CUALQUIER mes que se corra la facturación,
        # no solo enero. El chequeo "fecha_emision__year=año" ya evita duplicar
        # si el local ya se facturó antes en el mismo año.
        locales_anuales = LocalComercial.objects.filter(
            empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=True, cuota__gt=0,
        ).select_related("cliente")
        locales_anuales_ids = list(locales_anuales.values_list("id", flat=True))
        locales_anuales_con_factura = set(
            Factura.objects.filter(
                local_id__in=locales_anuales_ids, tipo_cuota="mantenimiento",
                estatus__in=["pendiente", "cobrada"], fecha_emision__year=año,
            ).values_list("local_id", flat=True)
        )
        for local in locales_anuales:
            if local.id not in locales_anuales_con_factura:
                last_num_cm += 1
                monto_anual = local.cuota * 12
                # NUEVO -- bulk_create, desglose explícito.
                mb, miva = calcular_iva_factura(monto_anual, "mantenimiento")
                facturas_a_crear.append(Factura(
                    empresa=empresa, cliente=local.cliente, local=local,
                    folio=f"CM-F{last_num_cm:05d}", fecha_emision=fecha_factura,
                    fecha_vencimiento=fecha_factura, monto=monto_anual,
                    monto_base=mb, monto_iva=miva,
                    tipo_cuota="mantenimiento", estatus="pendiente", 
                    observaciones=f"Cuota anual (${local.cuota}/mes × 12)",
                ))
                facturas_creadas += 1

    if facturar_areas:
        # areas = AreaComun.objects.filter(
        #     empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=False, cuota__gt=0,
        # ).select_related("cliente")
        areas = AreaComun.objects.filter(
            empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=False,
            es_cuota_variable=False, cuota__gt=0,
        ).select_related("cliente")

        areas_ids = list(areas.values_list("id", flat=True))
        areas_con_factura = set(
            Factura.objects.filter(
                area_comun_id__in=areas_ids, tipo_cuota="renta",
                estatus__in=["pendiente", "cobrada"],
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
                # NUEVO -- bulk_create, desglose explícito. "renta" es GRAVADA.
                mb, miva = calcular_iva_factura(area.cuota, "renta")
                facturas_a_crear.append(Factura(
                    empresa=empresa, cliente=area.cliente, area_comun=area,
                    folio=f"AC-F{last_num_ac:05d}", fecha_emision=fecha_factura,
                    fecha_vencimiento=fecha_factura, monto=area.cuota,
                    monto_base=mb, monto_iva=miva,
                    tipo_cuota="renta", estatus="pendiente", 
                    observaciones="Cuota mensual",
                ))
                facturas_creadas += 1

            if area.deposito and area.deposito > 0:
                existe_deposito = Factura.objects.filter(
                    cliente=area.cliente, area_comun=area, tipo_cuota="deposito",
                ).exists()
                if not existe_deposito:
                    last_num_dg += 1
                    # NUEVO -- "deposito" es EXENTO -- monto_base = monto, monto_iva = 0.
                    mb, miva = calcular_iva_factura(area.deposito, "deposito")
                    facturas_a_crear.append(Factura(
                        empresa=empresa, cliente=area.cliente, area_comun=area,
                        folio=f"DG-F{last_num_dg:05d}", fecha_emision=fecha_factura,
                        fecha_vencimiento=fecha_factura, monto=area.deposito,
                        monto_base=mb, monto_iva=miva,
                        tipo_cuota="deposito", estatus="pendiente", 
                        observaciones="Depósito en garantía",
                    ))

        # Cuota anual -- se revisa en CUALQUIER mes, mismo criterio que locales.
        # areas_anuales = AreaComun.objects.filter(
        #     empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=True, cuota__gt=0,
        # ).select_related("cliente")
        areas_anuales = AreaComun.objects.filter(
            empresa=empresa, activo=True, cliente__isnull=False, es_cuota_anual=True,
            es_cuota_variable=False, cuota__gt=0,
        ).select_related("cliente")

        areas_anuales_ids = list(areas_anuales.values_list("id", flat=True))
        areas_anuales_con_factura = set(
            Factura.objects.filter(
                area_comun_id__in=areas_anuales_ids, tipo_cuota="renta",
                estatus__in=["pendiente", "cobrada"], fecha_emision__year=año,
            ).values_list("area_comun_id", flat=True)
        )
        for area in areas_anuales:
            if area.id not in areas_anuales_con_factura:
                last_num_ac += 1
                monto_anual = area.cuota * 12
                # NUEVO -- bulk_create, desglose explícito.
                mb, miva = calcular_iva_factura(monto_anual, "renta")
                facturas_a_crear.append(Factura(
                    empresa=empresa, cliente=area.cliente, area_comun=area,
                    folio=f"AC-F{last_num_ac:05d}", fecha_emision=fecha_factura,
                    fecha_vencimiento=fecha_factura, monto=monto_anual,
                    monto_base=mb, monto_iva=miva,
                    tipo_cuota="renta", estatus="pendiente", 
                    observaciones=f"Cuota anual (${area.cuota}/mes × 12)"
                ))
                facturas_creadas += 1

    if facturas_a_crear:
        Factura.objects.bulk_create(facturas_a_crear, batch_size=50)
        # NUEVO -- aplica saldos a favor a cada factura recién creada
        # (bulk_create en Postgres regresa los objetos con pk ya asignado)
        for factura_nueva in facturas_a_crear:
            aplicar_saldos_a_favor(factura_nueva)

    return facturas_creadas, facturas_omitidas




# Se usa en 2 lugares:
#   1. Factura.save() -- para cualquier factura creada/editada con
#      .create() o .save() normal (Crear Factura manual, Grupos,
#      Pools de Vacancia, etc.)
#   2. generar_facturas_mes -- para las facturas que van por
#      bulk_create (locales/áreas mensuales y anuales), donde
#      save() NUNCA se ejecuta.
# ============================================================





# True = exento, False = gravado (16%)
TIPO_CUOTA_ES_EXENTO = {
    "mantenimiento": True,
    "deposito": True,
    "extraordinaria": True,
    "renta": False,
    "penalidad": False,
    "intereses": False,
}


def calcular_iva_factura(monto, tipo_cuota):
    """Regresa (monto_base, monto_iva) a partir de un monto TOTAL
    (con IVA ya incluido, si aplica) y el tipo_cuota de la factura."""
    if monto is None:
        return Decimal("0"), Decimal("0")

    monto = Decimal(str(monto))
    es_exento = TIPO_CUOTA_ES_EXENTO.get(tipo_cuota, True)

    if es_exento:
        return monto, Decimal("0")

    base = (monto / (Decimal("1") + IVA_TASA)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva = monto - base
    return base, iva