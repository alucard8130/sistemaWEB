
# Create your views here.
from datetime import date
from django.shortcuts import render, redirect,get_object_or_404
from areas.models import AreaComun
from clientes.models import Cliente
from empresas.models import Empresa
from locales.models import LocalComercial
from .forms import FacturaForm, PagoForm
from .models import Factura, Pago
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
#from django.db.models import Sum, F, ExpressionWrapper, fields
from django.db.models import F, OuterRef, Subquery, Sum, DecimalField, Value, ExpressionWrapper
from django.db.models.functions import Coalesce




@login_required
def crear_factura(request):
    if request.method == 'POST':
        form = FacturaForm(request.POST, user=request.user)
        if form.is_valid():
            factura = form.save(commit=False)
            if request.user.is_superuser:
                factura.empresa = factura.cliente.empresa
            else:
                factura.empresa = request.user.perfilusuario.empresa

            # Crear folio único
            count = Factura.objects.filter(fecha_emision__year=now().year).count() + 1
            factura.folio = f"MAN-{now().year}-{count:04d}"
            factura.save()
            messages.success(request, "Factura creada correctamente.")
            return redirect('lista_facturas')
    else:
        form = FacturaForm(user=request.user)

    return render(request, 'facturacion/crear_factura.html', {'form': form})

"""@login_required
def lista_facturas(request):
    if request.user.is_superuser:
        facturas = Factura.objects.all()
    else:
        empresa = request.user.perfilusuario.empresa
        facturas = Factura.objects.filter(empresa=empresa)

    return render(request, 'facturacion/lista_facturas.html', 
        {'facturas': facturas})
from empresas.models import Empresa"""

@login_required
def lista_facturas(request):
    empresas = Empresa.objects.all() if request.user.is_superuser else []
    empresa_id = request.GET.get('empresa')

    if request.user.is_superuser:
        if empresa_id:
            facturas = Factura.objects.filter(empresa_id=empresa_id)
        else:
            facturas = Factura.objects.all()
    else:
        empresa = request.user.perfilusuario.empresa
        facturas = Factura.objects.filter(empresa=empresa)

    return render(request, 'facturacion/lista_facturas.html', {
        'facturas': facturas,
        'empresas': empresas,
        'empresa_seleccionada': int(empresa_id) if empresa_id else None
    })


def facturar_mes_actual(request, facturar_locales=True, facturar_areas=True):
    hoy = date.today()
    año, mes = hoy.year, hoy.month

    facturas_creadas = 0

    if request.user.is_superuser:
        if facturar_locales:
            locales = LocalComercial.objects.filter(activo=True, cliente__isnull=False)
        if facturar_areas:
            areas = AreaComun.objects.filter(activo=True, cliente__isnull=False)
    else:
        empresa = request.user.perfilusuario.empresa
        if facturar_locales:
            locales = LocalComercial.objects.filter(empresa=empresa, activo=True, cliente__isnull=False)
        if facturar_areas:
            areas = AreaComun.objects.filter(empresa=empresa, activo=True, cliente__isnull=False)

    if facturar_locales:
        for local in locales:
            existe = Factura.objects.filter(
                cliente=local.cliente,
                local=local,
                fecha_emision__year=año,
                fecha_emision__month=mes
            ).exists()
            if not existe:
                folio = f"CM-{año}-{mes:02d}-{local.pk}"
                Factura.objects.create(
                    empresa=local.empresa,
                    cliente=local.cliente,
                    local=local,
                    folio=folio,
                    fecha_emision=hoy,
                    fecha_vencimiento=date(año, mes, 28),
                    monto=local.cuota,
                    estatus='pendiente',
                    observaciones='Factura generada automáticamente'
                )
                facturas_creadas += 1

    if facturar_areas:
        for area in areas:
            existe = Factura.objects.filter(
                cliente=area.cliente,
                area_comun=area,
                fecha_emision__year=año,
                fecha_emision__month=mes
            ).exists()
            if not existe:
                folio = f"AC-{año}-{mes:02d}-{area.pk}"
                Factura.objects.create(
                    empresa=area.empresa,
                    cliente=area.cliente,
                    area_comun=area,
                    folio=folio,
                    fecha_emision=hoy,
                    fecha_vencimiento=date(año, mes, 28),
                    monto=area.cuota,
                    estatus='pendiente',
                    observaciones='Factura generada automáticamente'
                )
                facturas_creadas += 1

    messages.success(request, f"{facturas_creadas} facturas generadas para {hoy.strftime('%B %Y')}")
    return redirect('lista_facturas')


#@login_required
#def confirmar_facturacion(request):
 #   if request.method == 'POST':
  #      facturar_locales = 'locales' in request.POST
   #     facturar_areas = 'areas' in request.POST
    #    return facturar_mes_actual(request, facturar_locales, facturar_areas)

    #return render(request, 'facturacion/confirmar_facturacion.html')

@login_required
def confirmar_facturacion(request):
    hoy = now().date()
    año, mes = hoy.year, hoy.month

    empresa = None
    if not request.user.is_superuser:
        empresa = request.user.perfilusuario.empresa

    # FILTRAR locales y áreas activos con cliente
    if request.user.is_superuser:
        locales = LocalComercial.objects.filter(activo=True, cliente__isnull=False)
        areas = AreaComun.objects.filter(activo=True, cliente__isnull=False)
    else:
        locales = LocalComercial.objects.filter(empresa=empresa, activo=True, cliente__isnull=False)
        areas = AreaComun.objects.filter(empresa=empresa, activo=True, cliente__isnull=False)

    # CONTAR locales no facturados aún este mes
    total_locales = sum(
        not Factura.objects.filter(cliente=l.cliente, local=l,
                                   fecha_emision__year=año, fecha_emision__month=mes).exists()
        for l in locales
    )

    total_areas = sum(
        not Factura.objects.filter(cliente=a.cliente, area_comun=a,
                                   fecha_emision__year=año, fecha_emision__month=mes).exists()
        for a in areas
    )

    if request.method == 'POST':
        facturar_locales = 'locales' in request.POST
        facturar_areas = 'areas' in request.POST
        return facturar_mes_actual(request, facturar_locales, facturar_areas)

    return render(request, 'facturacion/confirmar_facturacion.html', {
        'total_locales': total_locales,
        'total_areas': total_areas,
        'año': año,
        'mes': mes
    })

@login_required
def registrar_pago(request, factura_id):
    factura = get_object_or_404(Factura, pk=factura_id)

    if factura.estatus == 'pagada' or factura.saldo_pendiente <= 0:
        messages.warning(request, "La factura ya está completamente pagada. No se pueden registrar más pagos.")
        return redirect('lista_facturas')

    if request.method == 'POST':
        form = PagoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            if pago.monto > factura.saldo_pendiente:
                form.add_error('monto', f"El monto excede el saldo pendiente (${factura.saldo_pendiente:.2f}).")
            else:
                pago.factura = factura
                pago.registrado_por = request.user
                pago.save()
                factura.actualizar_estatus()
                messages.success(request, f"Pago registrado. Saldo restante: ${factura.saldo_pendiente:.2f}")
                return redirect('lista_facturas')
    else:
        form = PagoForm()

    return render(request, 'facturacion/registrar_pago.html', {
        'form': form,
        'factura': factura,
        'saldo': factura.saldo_pendiente,
    })

from django.db.models import Q

@login_required
def pagos_por_origen(request):
    tipo = request.GET.get('tipo')  # 'local' o 'area'
    pagos = Pago.objects.select_related('factura', 'factura__cliente', 'factura__empresa')

    if tipo == 'local':
        pagos = pagos.filter(factura__local__isnull=False)
    elif tipo == 'area':
        pagos = pagos.filter(factura__area_comun__isnull=False)

    if not request.user.is_superuser:
        pagos = pagos.filter(factura__empresa=request.user.perfilusuario.empresa)

    return render(request, 'facturacion/pagos_por_origen.html', {
        'pagos': pagos,
        'tipo': tipo,
    })

@login_required
def dashboard_saldos(request):
    hoy = date.today()
    hoy_30 = hoy + timedelta(days=30)
    hoy_60 = hoy + timedelta(days=60)
    hoy_90 = hoy + timedelta(days=90)

    rango = request.GET.get('rango')
    cliente_id = request.GET.get('cliente')
    empresa_id = request.GET.get('empresa') if request.user.is_superuser else request.user.perfilusuario.empresa.id

    facturas = Factura.objects.filter(estatus='pendiente', empresa_id=empresa_id)

    if cliente_id:
        facturas = facturas.filter(cliente_id=cliente_id)

    # Filtros de rango visual
    if rango == '0-30':
        facturas = facturas.filter(fecha_vencimiento__lte=hoy_30)
    elif rango == '31-60':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy_30, fecha_vencimiento__lte=hoy_60)
    elif rango == '61-90':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy_60, fecha_vencimiento__lte=hoy_90)
    elif rango == '90+':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy_90)

    # Subconsulta: total pagado por factura
    from facturacion.models import Pago

    pagos_subquery = Pago.objects.filter(factura=OuterRef('pk')) \
    .values('factura') \
    .annotate(total_pagado_dash=Coalesce(Sum('monto'), Value(0,output_field=DecimalField()))) \
    .values('total_pagado_dash')
    
    # Anotamos saldo pendiente
    facturas = facturas.annotate(
    total_pagado_dash=Coalesce(Subquery(pagos_subquery), Value(0,output_field=DecimalField())),
    saldo_pendiente_dash=ExpressionWrapper(
        F('monto') - Coalesce(Subquery(pagos_subquery), Value(0,output_field=DecimalField())),
        output_field=DecimalField()
    )
)    

    # Para el gráfico: totales por grupo
    saldo_0_30 = facturas.filter(fecha_vencimiento__lte=hoy_30).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_31_60 = facturas.filter(fecha_vencimiento__gt=hoy_30, fecha_vencimiento__lte=hoy_60).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_61_90 = facturas.filter(fecha_vencimiento__gt=hoy_60, fecha_vencimiento__lte=hoy_90).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_90_mas = facturas.filter(fecha_vencimiento__gt=hoy_90).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0


    #facturas = facturas.annotate(
     #   saldo=ExpressionWrapper(
      #      F('monto') - Sum('pagos__monto'),
       #     output_field=fields.DecimalField(max_digits=10, decimal_places=2)
        #)
    #).select_related('cliente', 'empresa', 'local', 'area_comun').order_by('-fecha_vencimiento')

    clientes = Cliente.objects.filter(empresa_id=empresa_id)
    empresas = Empresa.objects.all() if request.user.is_superuser else None

    return render(request, 'dashboard/saldos.html', {
        'facturas': facturas,
        'clientes': clientes,
        'empresas': empresas,
        'rango': rango,
        'cliente_id': int(cliente_id) if cliente_id else None,
        'saldo_0_30': saldo_0_30,
        'saldo_31_60': saldo_31_60,
        'saldo_61_90': saldo_61_90,
        'saldo_90_mas': saldo_90_mas,
    })