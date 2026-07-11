from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from conciliaciones.models import SaldoCuentaPeriodo
from conciliaciones.utils import calcular_saldo_acumulado_hasta, calcular_saldo_cuenta_periodo
from .models import  TraspasoBancario
from empresas.models import Empresa, CuentaBancaria
import datetime
from decimal import Decimal


@login_required
def lista_traspasos(request):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get('empresa_id')
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    traspasos = TraspasoBancario.objects.filter(
        empresa=empresa
    ).select_related('cuenta_origen', 'cuenta_destino').order_by('-fecha', '-fecha_registro')

    return render(request, 'traspasos/lista.html', {
        'traspasos': traspasos,
        'empresa': empresa,
    })


@login_required
def nuevo_traspaso(request):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get('empresa_id')
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)
    # Calcular saldo real de cada cuenta
    hoy = datetime.date.today()

    cuentas_con_saldo = []
    for cuenta in cuentas:
        # Buscar el período actual en SaldoCuentaPeriodo
        periodo = SaldoCuentaPeriodo.objects.filter(
            cuenta=cuenta,
            anio=hoy.year,
            mes=hoy.month
        ).first()

        if periodo:
            saldo = periodo.saldo_calculado
        else:
            # Si no existe el período, usar saldo_final del modelo
            saldo = cuenta.saldo_final or cuenta.saldo_inicial or 0

        cuentas_con_saldo.append({
            'id': cuenta.id,
            'banco': cuenta.banco,
            'numero_cuenta': cuenta.numero_cuenta,
            'tipo_cuenta': cuenta.get_tipo_cuenta_display(),
            'moneda': cuenta.moneda,
            'saldo_actual': saldo,
        })
        
    if request.method == 'POST':
        cuenta_origen_id = request.POST.get('cuenta_origen')
        cuenta_destino_id = request.POST.get('cuenta_destino')
        monto = request.POST.get('monto')
        fecha = request.POST.get('fecha')
        concepto = request.POST.get('concepto', '').strip()
        referencia = request.POST.get('referencia', '').strip()

        # Validaciones
        if cuenta_origen_id == cuenta_destino_id:
            messages.error(request, "La cuenta origen y destino no pueden ser la misma.")
            return render(request, 'traspasos/nuevo.html', {'cuentas': cuentas, 'empresa': empresa})

        try:
            monto = Decimal(monto)
            if monto <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "El monto debe ser un número mayor a cero.")
            return render(request, 'traspasos/nuevo.html', {'cuentas': cuentas, 'empresa': empresa})

        cuenta_origen = get_object_or_404(CuentaBancaria, pk=cuenta_origen_id, empresa=empresa)
        cuenta_destino = get_object_or_404(CuentaBancaria, pk=cuenta_destino_id, empresa=empresa)

        # Verificar saldo suficiente
        # saldo_origen = cuenta_origen.saldo_final or cuenta_origen.saldo_inicial
        periodo_origen = SaldoCuentaPeriodo.objects.filter(
            cuenta=cuenta_origen,
            anio=hoy.year,
            mes=hoy.month
        ).first()
        saldo_origen = periodo_origen.saldo_calculado if periodo_origen else (cuenta_origen.saldo_final or cuenta_origen.saldo_inicial or 0)

        hoy = datetime.date.today()
        saldo_base = calcular_saldo_acumulado_hasta(cuenta_origen, hoy.year, hoy.month)
        movs = calcular_saldo_cuenta_periodo(cuenta_origen, hoy.year, hoy.month)
        saldo_origen = saldo_base + movs['movimiento_neto']

        if saldo_origen < monto:
            messages.error(request, f"Saldo insuficiente en la cuenta origen. Saldo disponible: ${saldo_origen:,.2f}")
            return render(request, 'traspasos/nuevo.html', {'cuentas': cuentas, 'empresa': empresa})

        # Registrar traspaso y actualizar saldos en una transacción atómica
        with transaction.atomic():
            traspaso = TraspasoBancario.objects.create(
                empresa=empresa,
                cuenta_origen=cuenta_origen,
                cuenta_destino=cuenta_destino,
                monto=monto,
                fecha=fecha,
                concepto=concepto,
                referencia=referencia,
                estado='completado',
                creado_por=request.user,
            )

            # Actualizar saldo_final de cuenta origen (resta)
            saldo_origen_actual = cuenta_origen.saldo_final if cuenta_origen.saldo_final is not None else cuenta_origen.saldo_inicial
            cuenta_origen.saldo_final = saldo_origen_actual - monto
            cuenta_origen.save()

            # Actualizar saldo_final de cuenta destino (suma)
            saldo_destino_actual = cuenta_destino.saldo_final if cuenta_destino.saldo_final is not None else cuenta_destino.saldo_inicial
            cuenta_destino.saldo_final = saldo_destino_actual + monto
            cuenta_destino.save()

        messages.success(request, f"Traspaso de ${monto:,.2f} registrado correctamente.")
        return redirect('lista_traspasos')

    return render(request, 'traspasos/nuevo.html', {
        'cuentas': cuentas,
        'empresa': empresa,
        'fecha_hoy': hoy.isoformat(),
        'cuentas_con_saldo': cuentas_con_saldo,
    })


@login_required
def cancelar_traspaso(request, traspaso_id):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get('empresa_id')
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    traspaso = get_object_or_404(TraspasoBancario, pk=traspaso_id, empresa=empresa)

    if traspaso.estado == 'cancelado':
        messages.warning(request, "Este traspaso ya fue cancelado.")
        return redirect('lista_traspasos')

    if request.method == 'POST':
        with transaction.atomic():
            # Revertir saldos
            cuenta_origen = traspaso.cuenta_origen
            cuenta_destino = traspaso.cuenta_destino

            cuenta_origen.saldo_final = (cuenta_origen.saldo_final or cuenta_origen.saldo_inicial) + traspaso.monto
            cuenta_origen.save()

            cuenta_destino.saldo_final = (cuenta_destino.saldo_final or cuenta_destino.saldo_inicial) - traspaso.monto
            cuenta_destino.save()

            traspaso.estado = 'cancelado'
            traspaso.save()

        messages.success(request, "Traspaso cancelado y saldos revertidos correctamente.")
        return redirect('lista_traspasos')

    return render(request, 'traspasos/cancelar.html', {'traspaso': traspaso})




