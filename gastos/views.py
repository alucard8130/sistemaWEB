
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from openpyxl import Workbook
from empleados.models import Empleado
from empresas.models import Empresa
from presupuestos.models import Presupuesto
from proveedores.models import Proveedor
from .forms import GastoForm, PagoGastoForm, SubgrupoGastoForm, TipoGastoForm
from .models import Gasto, PagoGasto, SubgrupoGasto, TipoGasto
from datetime import datetime
from django.utils.timezone import localtime
from django.db.models.functions import TruncMonth
from django.db.models import Sum, Q, F, Value
import calendar
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date
# Create your views here.
@login_required
def subgrupo_gasto_crear(request):
    if request.method == 'POST':
        form = SubgrupoGastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('subgrupos_gasto_lista')
    else:
        form = SubgrupoGastoForm()
    return render(request, 'gastos/subgrupo_crear.html', {'form': form})

@login_required
def subgrupos_gasto_lista(request):
    subgrupos = SubgrupoGasto.objects.select_related('grupo').order_by('grupo__nombre', 'nombre')
    return render(request, 'gastos/subgrupos_lista.html', {'subgrupos': subgrupos})

@login_required
def tipos_gasto_lista(request):
    tipos = TipoGasto.objects.select_related('subgrupo__grupo').all()
    return render(request, 'gastos/tipos_gasto_lista.html', {'tipos': tipos})

@login_required
def tipo_gasto_crear(request):
    if request.method == 'POST':
        form = TipoGastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tipos_gasto_lista')
    else:
        form = TipoGastoForm()
    return render(request, 'gastos/tipo_gasto_form.html', {'form': form, 'modo': 'crear'})

@login_required
def tipo_gasto_editar(request, pk):
    tipo = get_object_or_404(TipoGasto, pk=pk)
    if request.method == 'POST':
        form = TipoGastoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            return redirect('tipos_gasto_lista')
    else:
        form = TipoGastoForm(instance=tipo)
    return render(request, 'gastos/tipo_gasto_form.html', {'form': form, 'modo': 'editar', 'tipo': tipo})

@login_required
def tipo_gasto_eliminar(request, pk):
    tipo = get_object_or_404(TipoGasto, pk=pk)
    if request.method == 'POST':
        tipo.delete()
        return redirect('tipos_gasto_lista')
    return render(request, 'gastos/tipo_gasto_confirmar_eliminar.html', {'tipo': tipo})

@login_required
def gastos_lista(request):
    gastos = Gasto.objects.all()
    proveedores = Proveedor.objects.filter(activo=True)
    empleados = Empleado.objects.filter(activo=True)
    tipos_gasto = TipoGasto.objects.all()

    proveedor_id = request.GET.get('proveedor')
    empleado_id = request.GET.get('empleado')
    tipo_gasto = request.GET.get('tipo_gasto')

    if request.user.is_superuser:
        gastos = Gasto.objects.all().select_related('empresa', 'proveedor', 'empleado', 'tipo_gasto')
    else:
        gastos = Gasto.objects.filter(empresa=request.user.perfilusuario.empresa)

    if proveedor_id:
        gastos = gastos.filter(proveedor_id=proveedor_id)
    if empleado_id:
        gastos = gastos.filter(empleado_id=empleado_id)
    if tipo_gasto:
        gastos = gastos.filter(tipo_gasto=tipo_gasto)

    return render(request, 'gastos/lista.html', {
        'gastos': gastos,                                         
        'proveedores': proveedores,
        'empleados': empleados,
        'tipos_gasto': tipos_gasto,
        'proveedor_id': proveedor_id,
        'empleado_id': empleado_id,
        'tipo_gasto_sel': tipo_gasto,
        })

@login_required
def gasto_nuevo(request):
    if request.method == 'POST':
        form = GastoForm(request.POST or None, request.FILES, user=request.user)
        if form.is_valid():
            gasto = form.save(commit=False)
            origen = form.cleaned_data['origen_tipo']
            if origen == 'proveedor':
                gasto.empleado = None
            elif origen == 'empleado':
                gasto.proveedor = None

            if not request.user.is_superuser:
                gasto.empresa = request.user.perfilusuario.empresa
                
            gasto.estatus = 'pendiente'    
            gasto.save()
            return redirect('gastos_lista')
    else:
        form = GastoForm(user=request.user)
        if not request.user.is_superuser:
            form.fields['empresa'].initial = request.user.perfilusuario.empresa
    return render(request, 'gastos/form.html', {'form': form, 'modo': 'crear'})

@login_required
def gasto_editar(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    if not request.user.is_superuser and gasto.empresa != request.user.perfilusuario.empresa:
        return redirect('gastos_lista')
    if request.method == 'POST':
        form = GastoForm(request.POST or None, request.FILES, instance=gasto, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('gastos_lista')
    else:
        form = GastoForm(instance=gasto, user=request.user)
    return render(request, 'gastos/form.html', {'form': form, 'modo': 'editar', 'gasto': gasto})

@login_required
def gasto_eliminar(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    if request.method == 'POST':
        gasto.delete()
        return redirect('gastos_lista')
    return render(request, 'gastos/confirmar_eliminar.html', {'gasto': gasto})

@login_required
def registrar_pago_gasto(request, gasto_id):
    gasto = get_object_or_404(Gasto, pk=gasto_id)
    pagos = gasto.pagos.all()
    saldo_restante = gasto.monto - sum([p.monto for p in pagos])

    if request.method == 'POST':
        form = PagoGastoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.gasto = gasto
            pago.registrado_por = request.user
            if pago.monto > saldo_restante:
                form.add_error('monto', f"El monto excede el saldo pendiente (${saldo_restante:.2f})")
            else:
                pago.save()
                gasto.actualizar_estatus()
                return redirect('gastos_lista')
    else:
        form = PagoGastoForm()

    return render(request, 'gastos/registrar_pago.html', {
        'form': form,
        'gasto': gasto,
        'saldo_restante': saldo_restante
    })


@login_required
def gasto_detalle(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    pagos = gasto.pagos.all().order_by('fecha_pago')

    return render(request, 'gastos/gasto_detalle.html', {
        'gasto': gasto,
        'pagos': pagos,
    })


@login_required
def reporte_pagos_gastos(request):
    es_super = request.user.is_superuser
    pagos = PagoGasto.objects.select_related('gasto', 'gasto__empresa', 'gasto__proveedor', 'gasto__empleado')

    # Filtros
    empresas = Empresa.objects.all() if es_super else Empresa.objects.filter(pk=request.user.perfilusuario.empresa.id)
    empresa_id = request.GET.get('empresa')
    proveedor_id = request.GET.get('proveedor')
    empleado_id = request.GET.get('empleado')
    forma_pago = request.GET.get('forma_pago')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if not es_super:
        pagos = pagos.filter(gasto__empresa=request.user.perfilusuario.empresa)
    elif empresa_id:
        pagos = pagos.filter(gasto__empresa_id=empresa_id)

    if proveedor_id:
        pagos = pagos.filter(gasto__proveedor_id=proveedor_id)
    if empleado_id:
        pagos = pagos.filter(gasto__empleado_id=empleado_id)
    if forma_pago:
        pagos = pagos.filter(forma_pago=forma_pago)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=parse_date(fecha_inicio))
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=parse_date(fecha_fin))

    total = pagos.aggregate(total=Sum('monto'))['total'] or 0

    proveedores = Proveedor.objects.all()
    empleados = Empleado.objects.all()
    FORMAS_PAGO = PagoGasto._meta.get_field('forma_pago').choices
    
    return render(request, 'gastos/reporte_pagos.html', {
        'pagos': pagos,
        'empresas': empresas,
        'empresa_id': empresa_id,
        'proveedores': proveedores,
        'empleados': empleados,
        'forma_pago_actual': forma_pago,
        'total': total,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'proveedor_id': proveedor_id,
        'empleado_id': empleado_id,
        'formas_pago': FORMAS_PAGO,
        
        # Si tienes catálogos de proveedores, empleados y formas de pago pásalos aquí
    })

@login_required
def dashboard_pagos_gastos(request):
    es_super = request.user.is_superuser
    anio_actual = datetime.now().year
    anio = int(request.GET.get('anio', anio_actual))

    empresas = Empresa.objects.all() if es_super else Empresa.objects.filter(id=request.user.perfilusuario.empresa.id)
    empresa_id = request.GET.get('empresa')
    proveedor_id = request.GET.get('proveedor')
    empleado_id = request.GET.get('empleado')
    forma_pago = request.GET.get('forma_pago')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # --- FILTROS BÁSICOS ---
    base_gastos = Q(fecha__year=anio)
    if es_super and empresa_id:
        base_gastos &= Q(empresa_id=empresa_id)
    elif not es_super:
        base_gastos &= Q(empresa=request.user.perfilusuario.empresa)
    if proveedor_id:
        base_gastos &= Q(proveedor_id=proveedor_id)
    if empleado_id:
        base_gastos &= Q(empleado_id=empleado_id)

    # Gastos registrados ese año y filtro empresa
    gastos = Gasto.objects.filter(base_gastos)

    # PAGOS
    pagos = PagoGasto.objects.filter(gasto__in=gastos)
    if forma_pago:
        pagos = pagos.filter(forma_pago=forma_pago)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)

    # PAGOS POR MES
    pagos_mes = pagos.annotate(mes=TruncMonth('fecha_pago')).values('mes').annotate(total=Sum('monto')).order_by('mes')
    pagos_mensuales = [0] * 12
    for p in pagos_mes:
        mes_idx = p['mes'].month - 1
        pagos_mensuales[mes_idx] = float(p['total'])

    # SALDOS PENDIENTES (por mes)
    saldos_mes = []
    for m in range(1, 13):
        # Gastos registrados ese mes
        gastos_mes = gastos.filter(fecha__month=m)
        monto_gastos_mes = gastos_mes.aggregate(total=Sum('monto'))['total'] or 0
        pagos_gastos_mes = PagoGasto.objects.filter(
            gasto__in=gastos_mes,
        ).aggregate(total=Sum('monto'))['total'] or 0
        saldo = float(monto_gastos_mes) - float(pagos_gastos_mes or 0)
        saldos_mes.append(saldo)

    # PRESUPUESTO POR MES
    presupuesto_mes = []
    for m in range(1, 13):
        pres = Presupuesto.objects.filter(empresa__in=empresas, anio=anio, mes=m).aggregate(total=Sum('monto'))['total'] or 0
        presupuesto_mes.append(float(pres))

    # KPI totales
    total_pagado = sum(pagos_mensuales)
    total_pendiente = sum(saldos_mes)
    total_presupuesto = sum(presupuesto_mes)

    # Catálogos
    proveedores = Proveedor.objects.all()
    empleados = Empleado.objects.all()
    FORMAS_PAGO = PagoGasto._meta.get_field('forma_pago').choices
    meses = [calendar.month_abbr[m] for m in range(1, 13)]

    return render(request, 'gastos/dashboard_pagos.html', {
        'empresas': empresas,
        'empresa_id': empresa_id,
        'anio': anio,
        'total_pagado': total_pagado,
        'total_pendiente': total_pendiente,
        'total_presupuesto': total_presupuesto,
        'meses': meses,
        'pagos_mensuales': pagos_mensuales,
        'saldos_mes': saldos_mes,
        'presupuesto_mes': presupuesto_mes,
        'proveedores': proveedores,
        'empleados': empleados,
        'proveedor_id': proveedor_id,
        'empleado_id': empleado_id,
        'formas_pago': FORMAS_PAGO,
        'forma_pago_actual': forma_pago,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'es_super': es_super,
    })

#exportar pagos de gastos a Excel
@login_required
def exportar_pagos_gastos_excel(request):
    es_super = request.user.is_superuser
    anio = request.GET.get('anio')
    if anio and anio.isdigit():
        anio = int(anio)
    else:
        anio = datetime.now().year
    empresa_id = request.GET.get('empresa')
    proveedor_id = request.GET.get('proveedor')
    empleado_id = request.GET.get('empleado')
    forma_pago = request.GET.get('forma_pago')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    
    # Filtro de empresa
    if es_super and empresa_id:
        gastos = Gasto.objects.filter(empresa_id=empresa_id, fecha__year=anio)
    else:
        gastos = Gasto.objects.filter(empresa=request.user.perfilusuario.empresa, fecha__year=anio)

    # Otros filtros
    if proveedor_id:
        gastos = gastos.filter(proveedor_id=proveedor_id)
    if empleado_id:
        gastos = gastos.filter(empleado_id=empleado_id)
    if fecha_inicio:
        gastos = gastos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        gastos = gastos.filter(fecha__lte=fecha_fin)

    # Solo los pagos
    pagos = PagoGasto.objects.filter(gasto__in=gastos)
    if forma_pago:
        pagos = pagos.filter(forma_pago=forma_pago)

    # --- Generar Excel ---
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos de Gastos"
    ws.append([
        "Fecha pago", "Empresa", "Proveedor/Empleado", "Concepto", 
        "Forma de pago", "Monto", "Estatus"
    ])

    for pago in pagos.select_related('gasto', 'gasto__empresa', 'gasto__proveedor', 'gasto__empleado'):
        gasto = pago.gasto
        # Mostrar proveedor o empleado
        origen = gasto.proveedor.nombre if gasto.proveedor else (
            gasto.empleado.nombre if gasto.empleado else ''
        )
        ws.append([
            pago.fecha_pago.strftime('%d/%m/%Y') if pago.fecha_pago else '',
            gasto.empresa.nombre if gasto.empresa else '',
            origen,
            gasto.descripcion,
            pago.get_forma_pago_display(),
            float(pago.monto),
            gasto.estatus
        ])

    # --- Respuesta HTTP ---
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"pagos_gastos_{anio}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response
