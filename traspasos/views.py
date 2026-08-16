import datetime
import re
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from clientes.models import Cliente
from conciliaciones.models import SaldoCuentaPeriodo
from conciliaciones.utils import (
    _rendimiento_en_rango,
    _saldo_inversion_a_fecha,
    _variacion,
    calcular_saldo_acumulado_hasta,
    calcular_saldo_cuenta_periodo,
    validar_periodo_abierto,
)
from empresas.models import CuentaBancaria, Empresa
from facturacion.models import (
    CobroOtrosIngresos,
    FacturaOtrosIngresos,
    Pago,
    TipoOtroIngreso,
)
from gastos.models import Gasto, PagoGasto, TipoGasto
from proveedores.models import Proveedor

from .models import TraspasoBancario


@login_required
def lista_traspasos(request):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    traspasos = (
        TraspasoBancario.objects.filter(empresa=empresa)
        .select_related("cuenta_origen", "cuenta_destino")
        .order_by("-fecha", "-fecha_registro")
    )

    return render(
        request,
        "traspasos/lista.html",
        {
            "traspasos": traspasos,
            "empresa": empresa,
        },
    )


@login_required
def nuevo_traspaso(request):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)
    # Calcular saldo real de cada cuenta
    hoy = datetime.date.today()

    cuentas_con_saldo = []
    for cuenta in cuentas:
        # NUEVO -- siempre el cálculo completo (incluye cuotas, gastos,
        # otros ingresos y traspasos), nunca el campo suelto saldo_final,
        # que no se actualiza con esos movimientos.
        saldo_base = calcular_saldo_acumulado_hasta(cuenta, hoy.year, hoy.month)
        movs = calcular_saldo_cuenta_periodo(cuenta, hoy.year, hoy.month)
        saldo = saldo_base + movs["movimiento_neto"]
 
        cuentas_con_saldo.append(
            {
                "id": cuenta.id,
                "banco": cuenta.banco,
                "numero_cuenta": cuenta.numero_cuenta,
                "tipo_cuenta": cuenta.get_tipo_cuenta_display(),
                "moneda": cuenta.moneda,
                "saldo_actual": saldo,
            }
        )

    if request.method == "POST":
        cuenta_origen_id = request.POST.get("cuenta_origen")
        cuenta_destino_id = request.POST.get("cuenta_destino")
        monto = request.POST.get("monto")
        fecha = request.POST.get("fecha")
        concepto = request.POST.get("concepto", "").strip()
        referencia = request.POST.get("referencia", "").strip()

        # Validaciones
        if cuenta_origen_id == cuenta_destino_id:
            messages.error(
                request, "La cuenta origen y destino no pueden ser la misma."
            )
            return render(
                request,
                "traspasos/nuevo.html",
                {"cuentas": cuentas, "empresa": empresa},
            )

        try:
            monto = Decimal(monto)
            if monto <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "El monto debe ser un número mayor a cero.")
            return render(
                request,
                "traspasos/nuevo.html",
                {"cuentas": cuentas, "empresa": empresa},
            )

        cuenta_origen = get_object_or_404(
            CuentaBancaria, pk=cuenta_origen_id, empresa=empresa
        )
        cuenta_destino = get_object_or_404(
            CuentaBancaria, pk=cuenta_destino_id, empresa=empresa
        )

        # # Verificar saldo suficiente
        # # saldo_origen = cuenta_origen.saldo_final or cuenta_origen.saldo_inicial
        # periodo_origen = SaldoCuentaPeriodo.objects.filter(
        #     cuenta=cuenta_origen, anio=hoy.year, mes=hoy.month
        # ).first()
        # saldo_origen = (
        #     periodo_origen.saldo_calculado
        #     if periodo_origen
        #     else (cuenta_origen.saldo_final or cuenta_origen.saldo_inicial or 0)
        # )

        hoy = datetime.date.today()
        saldo_base = calcular_saldo_acumulado_hasta(cuenta_origen, hoy.year, hoy.month)
        movs = calcular_saldo_cuenta_periodo(cuenta_origen, hoy.year, hoy.month)
        saldo_origen = saldo_base + movs["movimiento_neto"]

        if saldo_origen < monto:
            messages.error(
                request,
                f"Saldo insuficiente en la cuenta origen. Saldo disponible: ${saldo_origen:,.2f}",
            )
            return render(
                request,
                "traspasos/nuevo.html",
                {"cuentas": cuentas, "empresa": empresa},
            )

        # Registrar traspaso
        with transaction.atomic():
            traspaso = TraspasoBancario.objects.create(
                empresa=empresa,
                cuenta_origen=cuenta_origen,
                cuenta_destino=cuenta_destino,
                monto=monto,
                fecha=fecha,
                concepto=concepto,
                referencia=referencia,
                estado="completado",
                creado_por=request.user,
            )

            # saldo_origen_actual = (
            #     cuenta_origen.saldo_final
            #     if cuenta_origen.saldo_final is not None
            #     else cuenta_origen.saldo_inicial
            # )
            # cuenta_origen.saldo_final = saldo_origen_actual - monto
            # cuenta_origen.save()

            # saldo_destino_actual = (
            #     cuenta_destino.saldo_final
            #     if cuenta_destino.saldo_final is not None
            #     else cuenta_destino.saldo_inicial
            # )
            # cuenta_destino.saldo_final = saldo_destino_actual + monto
            # cuenta_destino.save()

        messages.success(
            request, f"Traspaso de ${monto:,.2f} registrado correctamente."
        )
        return redirect("lista_traspasos")

    return render(
        request,
        "traspasos/nuevo.html",
        {
            "cuentas": cuentas,
            "empresa": empresa,
            "fecha_hoy": hoy.isoformat(),
            "cuentas_con_saldo": cuentas_con_saldo,
            "proveedores": Proveedor.objects.filter(
                empresa=empresa, activo=True
            ).order_by("nombre"),
            "tipos_gasto": TipoGasto.objects.filter(empresa=empresa).order_by("nombre"),
        },
    )


@login_required
def cancelar_traspaso(request, traspaso_id):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    traspaso = get_object_or_404(TraspasoBancario, pk=traspaso_id, empresa=empresa)

    if traspaso.estado == "cancelado":
        messages.warning(request, "Este traspaso ya fue cancelado.")
        return redirect("lista_traspasos")

    if request.method == "POST":
        with transaction.atomic():
            # Revertir saldos
            #cuenta_origen = traspaso.cuenta_origen
            #cuenta_destino = traspaso.cuenta_destino

            # cuenta_origen.saldo_final = (
            #     cuenta_origen.saldo_final or cuenta_origen.saldo_inicial
            # ) + traspaso.monto
            # cuenta_origen.save()

            # cuenta_destino.saldo_final = (
            #     cuenta_destino.saldo_final or cuenta_destino.saldo_inicial
            # ) - traspaso.monto
            # cuenta_destino.save()

            traspaso.estado = "cancelado"
            traspaso.save()

        messages.success(
            request, "Traspaso cancelado y saldos revertidos correctamente."
        )
        return redirect("lista_traspasos")

    return render(request, "traspasos/cancelar.html", {"traspaso": traspaso})


@login_required
def nuevo_movimiento_inversion(request):
    perfil = getattr(request.user, "perfilusuario", None)
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = perfil.empresa

    hoy = datetime.date.today()

    cuentas_inversion = CuentaBancaria.objects.filter(
        empresa=empresa, activa=True, tipo_cuenta="INVERSION"
    )
    cuentas_todas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)

    if request.method == "POST":
        cuenta_inversion_id = request.POST.get("cuenta_inversion")
        cuenta_contraparte_id = request.POST.get(
            "cuenta_contraparte"
        )  # no aplica para rendimiento
        tipo_movimiento = request.POST.get("tipo_movimiento")
        monto_raw = request.POST.get("monto", "").strip()
        fecha_str = request.POST.get("fecha")
        concepto_extra = request.POST.get("concepto", "").strip()

        if tipo_movimiento not in ("incremento", "rendimiento", "retiro"):
            messages.error(request, "Selecciona un tipo de movimiento válido.")
            return redirect("nuevo_movimiento_inversion")

        cuenta_inversion = get_object_or_404(
            CuentaBancaria,
            pk=cuenta_inversion_id,
            empresa=empresa,
            tipo_cuenta="INVERSION",
        )

        try:
            fecha = datetime.date.fromisoformat(fecha_str)
        except (ValueError, TypeError):
            messages.error(request, "Fecha inválida.")
            return redirect("nuevo_movimiento_inversion")

        try:
            monto = Decimal(monto_raw)
            if monto <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "El monto debe ser un número mayor a cero.")
            return redirect("nuevo_movimiento_inversion")

        ok, error = validar_periodo_abierto(cuenta_inversion, fecha, user=request.user)
        if not ok:
            messages.error(request, error)
            return redirect("nuevo_movimiento_inversion")

        # --- RENDIMIENTO: ingreso directo a la inversión, sin contraparte ---
        if tipo_movimiento == "rendimiento":
            # --- Encontrar el Cliente que representa al banco ---
            nombre_banco = cuenta_inversion.get_banco_display()
            cliente_banco = Cliente.objects.filter(
                empresa=empresa, nombre__iexact=nombre_banco
            ).first()
            if not cliente_banco:
                cliente_banco = Cliente.objects.filter(
                    empresa=empresa, nombre__icontains=nombre_banco
                ).first()

            if not cliente_banco:
                cliente_banco = Cliente.objects.create(
                    empresa=empresa,
                    nombre=nombre_banco,
                    activo=True,
                )
                return redirect("nuevo_movimiento_inversion")

            tipo_ingreso, _ = TipoOtroIngreso.objects.get_or_create(
                empresa=empresa, nombre="Rendimientos Financieros"
            )

            with transaction.atomic():
                # --- Crear la factura de otros ingresos + su cobro, con folio único ---
                prefix = "REND-"
                guardado = False
                for intento in range(5):
                    try:
                        last_folio = (
                            FacturaOtrosIngresos.objects.select_for_update()
                            .filter(empresa=empresa, folio__startswith=prefix)
                            .order_by("-folio")
                            .values_list("folio", flat=True)
                            .first()
                        )
                        last_num = (
                            int(last_folio.replace(prefix, ""))
                            if last_folio and re.match(r"^REND-\d{5}$", last_folio)
                            else 0
                        )
                        folio = f"{prefix}{last_num + 1:05d}"

                        factura_oi = FacturaOtrosIngresos.objects.create(
                            empresa=empresa,
                            cliente=cliente_banco,
                            tipo_ingreso=tipo_ingreso,
                            folio=folio,
                            fecha_vencimiento=fecha,
                            monto=monto,
                            observaciones=f"Rendimiento de inversión{' — ' + concepto_extra if concepto_extra else ''}",
                            estatus="pendiente",
                        )
                        cobro = CobroOtrosIngresos.objects.create(
                            factura=factura_oi,
                            fecha_cobro=fecha,
                            monto=monto,
                            forma_cobro="transferencia",
                            cuenta_bancaria=cuenta_inversion,
                            registrado_por=request.user,
                            observaciones="Aplicado automáticamente desde movimiento de inversión",
                        )
                        factura_oi.actualizar_estatus()
                        guardado = True
                        break
                    except IntegrityError:
                        continue

                if not guardado:
                    messages.error(
                        request, "No se pudo generar el folio. Intenta de nuevo."
                    )
                    return redirect("nuevo_movimiento_inversion")

            messages.success(
                request,
                f"✅ Rendimiento de ${monto:,.2f} registrado como otro ingreso ({factura_oi.folio}), sumado al saldo de {cuenta_inversion}.",
            )
            return redirect("reporte_inversion")

        # --- INCREMENTO o RETIRO: traspaso real entre dos cuentas ---
        if not cuenta_contraparte_id:
            messages.error(request, "Selecciona la cuenta contraparte.")
            return redirect("nuevo_movimiento_inversion")

        cuenta_contraparte = get_object_or_404(
            CuentaBancaria, pk=cuenta_contraparte_id, empresa=empresa
        )

        if tipo_movimiento == "incremento":
            cuenta_origen, cuenta_destino = cuenta_contraparte, cuenta_inversion
            etiqueta = "Incremento de inversión"
        else:  # retiro
            cuenta_origen, cuenta_destino = cuenta_inversion, cuenta_contraparte
            etiqueta = "Retiro / liquidación de inversión"

        saldo_base = calcular_saldo_acumulado_hasta(cuenta_origen, hoy.year, hoy.month)
        movs = calcular_saldo_cuenta_periodo(cuenta_origen, hoy.year, hoy.month)
        saldo_origen = saldo_base + movs["movimiento_neto"]

        if saldo_origen < monto:
            messages.error(
                request,
                f"Saldo insuficiente en {cuenta_origen}. Saldo disponible: ${saldo_origen:,.2f}",
            )
            return redirect("nuevo_movimiento_inversion")

        concepto_final = (
            f"{etiqueta} — {cuenta_inversion.banco} {cuenta_inversion.numero_cuenta}"
        )
        if concepto_extra:
            concepto_final += f" ({concepto_extra})"

        with transaction.atomic():
            TraspasoBancario.objects.create(
                empresa=empresa,
                cuenta_origen=cuenta_origen,
                cuenta_destino=cuenta_destino,
                monto=monto,
                fecha=fecha,
                concepto=concepto_final,
                estado="completado",
                creado_por=request.user,
                es_inversion=True,
                tipo_movimiento_inversion=tipo_movimiento,
            )

        messages.success(request, f"✅ {etiqueta} registrado: ${monto:,.2f}.")
        return redirect("reporte_inversion")

    return render(
        request,
        "inversiones/nuevo_movimiento_inversion.html",
        {
            "cuentas_inversion": cuentas_inversion,
            "cuentas_todas": cuentas_todas,
            "proveedores": Proveedor.objects.filter(
                empresa=empresa, activo=True
            ).order_by("nombre"),
            "tipos_gasto": TipoGasto.objects.filter(empresa=empresa).order_by("nombre"),
            "fecha_hoy": hoy.isoformat(),
        },
    )


@login_required
def reporte_inversion(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get('empresa_id')
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = perfil.empresa

    hoy = datetime.date.today()

    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - datetime.timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    try:
        fecha_mismo_dia_anio_anterior = hoy.replace(year=hoy.year - 1)
    except ValueError:
        fecha_mismo_dia_anio_anterior = hoy.replace(year=hoy.year - 1, day=28)

    primer_dia_anio_actual = hoy.replace(month=1, day=1)
    primer_dia_anio_anterior = hoy.replace(year=hoy.year - 1, month=1, day=1)

    cuentas_inversion = CuentaBancaria.objects.filter(empresa=empresa, activa=True, tipo_cuenta='INVERSION')

    resumen_por_cuenta = []
    for cuenta in cuentas_inversion:
        entrantes = TraspasoBancario.objects.filter(cuenta_destino=cuenta, es_inversion=True, estado='completado')
        salientes = TraspasoBancario.objects.filter(cuenta_origen=cuenta, es_inversion=True, estado='completado')
        rendimientos_qs = CobroOtrosIngresos.objects.filter(
            cuenta_bancaria=cuenta, factura__tipo_ingreso__nombre='Rendimientos Financieros'
        )

        total_incrementos = entrantes.filter(tipo_movimiento_inversion='incremento').aggregate(t=Sum('monto'))['t'] or Decimal('0')
        total_retiro = salientes.filter(tipo_movimiento_inversion='retiro').aggregate(t=Sum('monto'))['t'] or Decimal('0')
        total_rendimiento = rendimientos_qs.aggregate(t=Sum('monto'))['t'] or Decimal('0')

        saldo_actual = _saldo_inversion_a_fecha(cuenta, hoy)
        saldo_mes_anterior = _saldo_inversion_a_fecha(cuenta, ultimo_dia_mes_anterior)
        saldo_anio_anterior = _saldo_inversion_a_fecha(cuenta, fecha_mismo_dia_anio_anterior)

        diff_saldo_mes, pct_saldo_mes = _variacion(saldo_actual, saldo_mes_anterior)
        diff_saldo_anio, pct_saldo_anio = _variacion(saldo_actual, saldo_anio_anterior)

        rendimiento_mes_actual = _rendimiento_en_rango(cuenta, primer_dia_mes_actual, hoy)
        rendimiento_mes_anterior = _rendimiento_en_rango(cuenta, primer_dia_mes_anterior, ultimo_dia_mes_anterior)
        diff_rend_mes, pct_rend_mes = _variacion(rendimiento_mes_actual, rendimiento_mes_anterior)

        rendimiento_ytd_actual = _rendimiento_en_rango(cuenta, primer_dia_anio_actual, hoy)
        rendimiento_ytd_anterior = _rendimiento_en_rango(cuenta, primer_dia_anio_anterior, fecha_mismo_dia_anio_anterior)
        diff_rend_anio, pct_rend_anio = _variacion(rendimiento_ytd_actual, rendimiento_ytd_anterior)

        # --- Historial COMPLETO (ya no se recorta a [:20] aquí) ---
        movimientos = []
        for t in entrantes:
            movimientos.append({
                'id': t.id, 'puede_cancelar': True,
                'fecha': t.fecha, 'tipo': 'Incremento', 'badge': 'primary',
                'direccion': f"de {t.cuenta_origen}", 'entra': True,
                'monto': t.monto, 'concepto': t.concepto,
            })
        for t in salientes:
            movimientos.append({
                'id': t.id, 'puede_cancelar': True,
                'fecha': t.fecha, 'tipo': 'Retiro / Liquidación', 'badge': 'danger',
                'direccion': f"a {t.cuenta_destino}", 'entra': False,
                'monto': t.monto, 'concepto': t.concepto,
            })
        for c in rendimientos_qs:
            movimientos.append({
                'id': None, 'puede_cancelar': False,
                'fecha': c.fecha_cobro, 'tipo': 'Rendimiento', 'badge': 'success',
                'direccion': "crece dentro de la cuenta", 'entra': True,
                'monto': c.monto, 'concepto': c.observaciones,
            })
        movimientos.sort(key=lambda m: m['fecha'], reverse=True)

        # --- NUEVO: paginación independiente por cuenta ---
        # Cada cuenta usa su propio parámetro de página en la URL
        # (?pagina_5=2, ?pagina_8=3, etc.) para no interferir entre sí.
        param_pagina = f'pagina_{cuenta.id}'
        numero_pagina = request.GET.get(param_pagina, 1)
        paginator = Paginator(movimientos, 15)  # 15 movimientos por página
        movimientos_pagina = paginator.get_page(numero_pagina)

        resumen_por_cuenta.append({
            'cuenta': cuenta,
            'total_incrementos': total_incrementos,
            'total_rendimiento': total_rendimiento,
            'total_retiro': total_retiro,
            'saldo_actual': saldo_actual,
            'saldo_mes_anterior': saldo_mes_anterior,
            'saldo_anio_anterior': saldo_anio_anterior,
            'diff_saldo_mes': diff_saldo_mes, 'pct_saldo_mes': pct_saldo_mes,
            'diff_saldo_anio': diff_saldo_anio, 'pct_saldo_anio': pct_saldo_anio,
            'rendimiento_mes_actual': rendimiento_mes_actual,
            'diff_rend_mes': diff_rend_mes, 'pct_rend_mes': pct_rend_mes,
            'rendimiento_ytd_actual': rendimiento_ytd_actual,
            'diff_rend_anio': diff_rend_anio, 'pct_rend_anio': pct_rend_anio,
            'movimientos_pagina': movimientos_pagina,  # NUEVO -- reemplaza a 'movimientos'
            'param_pagina': param_pagina,               # NUEVO -- para armar los links en el template
        })

    return render(request, 'inversiones/reporte_inversion.html', {
        'resumen_por_cuenta': resumen_por_cuenta,
        'ultimo_dia_mes_anterior': ultimo_dia_mes_anterior,
        'fecha_mismo_dia_anio_anterior': fecha_mismo_dia_anio_anterior,
        'hoy': hoy,
    })



@login_required
def registrar_retencion_inversion(request):
    perfil = getattr(request.user, "perfilusuario", None)
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = perfil.empresa

    hoy = datetime.date.today()
    cuentas_inversion = CuentaBancaria.objects.filter(
        empresa=empresa, activa=True, tipo_cuenta="INVERSION"
    )
    proveedores = Proveedor.objects.filter(empresa=empresa, activo=True).order_by(
        "nombre"
    )
    tipos_gasto = TipoGasto.objects.filter(empresa=empresa).order_by("nombre")

    if request.method == "POST":
        cuenta_id = request.POST.get("cuenta_inversion")
        fecha_str = request.POST.get("fecha")
        monto_raw = request.POST.get("monto", "").strip()
        proveedor_id = request.POST.get("proveedor_id")
        tipo_gasto_id = request.POST.get("tipo_gasto_id")
        observaciones = request.POST.get("observaciones", "").strip()

        cuenta_inversion = get_object_or_404(
            CuentaBancaria, pk=cuenta_id, empresa=empresa, tipo_cuenta="INVERSION"
        )

        try:
            fecha = datetime.date.fromisoformat(fecha_str)
        except (ValueError, TypeError):
            messages.error(request, "Fecha inválida.")
            return redirect("registrar_retencion_inversion")

        try:
            monto = Decimal(monto_raw)
            if monto <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "El monto debe ser un número mayor a cero.")
            return redirect("registrar_retencion_inversion")

        if not proveedor_id or not tipo_gasto_id:
            messages.error(request, "Elige el proveedor (banco) y la cuenta de gasto.")
            return redirect("registrar_retencion_inversion")

        proveedor = get_object_or_404(Proveedor, pk=proveedor_id, empresa=empresa)
        tipo_gasto = get_object_or_404(TipoGasto, pk=tipo_gasto_id, empresa=empresa)

        with transaction.atomic():
            gasto = Gasto.objects.create(
                empresa=empresa,
                proveedor=proveedor,
                tipo_gasto=tipo_gasto,
                fecha=fecha,
                monto=monto,
                descripcion=f"Retención de ISR sobre rendimiento de inversión — {cuenta_inversion.banco} {cuenta_inversion.numero_cuenta}",
                estatus="pendiente",
                observaciones=observaciones
                or "El banco retuvo este monto antes de pagar; no representa una salida de efectivo de ninguna cuenta.",
            )
            # Sin cuenta_bancaria: esta retención nunca salió de ninguna
            # cuenta tuya, el banco simplemente no la pagó.
            PagoGasto.objects.create(
                gasto=gasto,
                fecha_pago=fecha,
                monto=monto,
                forma_pago="transferencia",
                referencia=f"Retención de ISR — {cuenta_inversion.banco} {cuenta_inversion.numero_cuenta}",
                registrado_por=request.user,
                cuenta_bancaria=None,
            )
            gasto.actualizar_estatus()

        messages.success(
            request,
            f"✅ Retención de ISR por ${monto:,.2f} registrada como gasto ({gasto.id}), ya marcada como pagada.",
        )
        return redirect("reporte_inversion")

    return render(
        request,
        "inversiones/registrar_retencion_inversion.html",
        {
            "cuentas_inversion": cuentas_inversion,
            "proveedores": proveedores,
            "tipos_gasto": tipos_gasto,
            "fecha_hoy": hoy.isoformat(),
        },
    )


@login_required
def cancelar_movimiento_inversion(request, traspaso_id):
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        empresa_id = request.session.get('empresa_id')
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = perfil.empresa if perfil else None

    traspaso = get_object_or_404(
        TraspasoBancario, pk=traspaso_id, empresa=empresa,
        es_inversion=True, estado='completado',
    )

    # Solo se permite cancelar incrementos y retiros -- nunca rendimientos
    # ni nada que ya haya generado factura/gasto por su cuenta.
    if traspaso.tipo_movimiento_inversion not in ('incremento', 'retiro'):
        messages.error(request, "Este tipo de movimiento no se puede cancelar desde aquí.")
        return redirect('reporte_inversion')

    if request.method != 'POST':
        return redirect('reporte_inversion')

    with transaction.atomic():
        # Revertir el efecto en los saldos cacheados de las cuentas
        # cuenta_origen = traspaso.cuenta_origen
        # cuenta_destino = traspaso.cuenta_destino

        # saldo_origen_actual = cuenta_origen.saldo_final if cuenta_origen.saldo_final is not None else cuenta_origen.saldo_inicial
        # cuenta_origen.saldo_final = saldo_origen_actual + traspaso.monto
        # cuenta_origen.save()

        # saldo_destino_actual = cuenta_destino.saldo_final if cuenta_destino.saldo_final is not None else cuenta_destino.saldo_inicial
        # cuenta_destino.saldo_final = saldo_destino_actual - traspaso.monto
        # cuenta_destino.save()

        # No se borra -- se marca como cancelado, para no perder rastro.
        # Los cálculos de saldo (tanto en inversión como en saldos_periodo)
        # ya excluyen todo lo que no esté en estado='completado'.
        traspaso.estado = 'cancelado'
        traspaso.save()

    messages.success(
        request,
        f"✅ Movimiento cancelado: {traspaso.get_tipo_movimiento_inversion_display()} de ${traspaso.monto:,.2f} ({traspaso.fecha})."
    )
    return redirect('reporte_inversion')
