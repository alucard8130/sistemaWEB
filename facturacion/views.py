
# Create your views here.
from django.shortcuts import render, redirect,get_object_or_404
from areas.models import AreaComun
from clientes.models import Cliente
from empresas.models import Empresa
from locales.models import LocalComercial
from .forms import FacturaForm, PagoForm
from .models import Factura, Pago
from django.utils.timezone import now
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
#from django.db.models import Sum, F, ExpressionWrapper, fields
from django.db.models import F, OuterRef, Subquery, Sum, DecimalField, Value, ExpressionWrapper
from django.db.models.functions import Coalesce
import openpyxl
from django.http import HttpResponse




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
    hoy = timezone.now().date()

    rango = request.GET.get('rango')
    cliente_id = request.GET.get('cliente')
    empresa_id = request.GET.get('empresa') if request.user.is_superuser else request.user.perfilusuario.empresa.id

    facturas = Factura.objects.filter(estatus='pendiente', empresa_id=empresa_id)

    if cliente_id:
        facturas = facturas.filter(cliente_id=cliente_id)

    # Filtros de rango visual
    if rango == '0-30':
        facturas = facturas.filter(fecha_vencimiento__lte=hoy - timedelta(days=30))
    elif rango == '31-60':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=30), fecha_vencimiento__lte=hoy - timedelta(days=60))
    elif rango == '61-90':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=60), fecha_vencimiento__lte=hoy - timedelta(days=90))
    elif rango == '90+':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=180))

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
    saldo_0_30 = facturas.filter(fecha_vencimiento__lte=hoy- timedelta(days=30)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_31_60 = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=30), fecha_vencimiento__lte=hoy - timedelta(days=60)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_61_90 = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=60), fecha_vencimiento__lte=hoy - timedelta(days=90)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_90_mas = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=180)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0


    clientes = Cliente.objects.filter(empresa_id=empresa_id)
    empresas = Empresa.objects.all() if request.user.is_superuser else None

    #KPI de pagos
    # Filtrar pagos activos
    pagos = Pago.objects.filter(factura__activo=True)

    if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
        empresa = request.user.perfilusuario.empresa
        pagos = pagos.filter(factura__empresa=empresa)
    else:
        empresa = None

    pagos_locales = pagos.filter(factura__local__isnull=False).aggregate(total=Sum('monto'))['total'] or 0
    pagos_areas = pagos.filter(factura__area_comun__isnull=False).aggregate(total=Sum('monto'))['total'] or 0


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
        'pagos_locales': pagos_locales,
        'pagos_areas': pagos_areas,
        'empresa': empresa,
    })


@login_required
def cartera_vencida(request):
    hoy = timezone.now().date()
    filtro = request.GET.get('rango')

    facturas = Factura.objects.filter(
        estatus='pendiente',
        fecha_vencimiento__lt=hoy,
        activo=True
    )
     # Filtrar por empresa
    if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
        facturas = facturas.filter(empresa=request.user.perfilusuario.empresa)
    elif request.GET.get('empresa'):
        facturas = facturas.filter(empresa_id=request.GET['empresa'])
    
    # Filtrar por cliente
    if request.GET.get('cliente'):
        facturas = facturas.filter(cliente_id=request.GET['cliente'])


    # Aplicar filtros de rango de días vencidos
    if filtro == 'menor30':
        facturas = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=30))
    elif filtro == '30a60':
        facturas = facturas.filter(
            fecha_vencimiento__lte=hoy - timedelta(days=30),
            fecha_vencimiento__gt=hoy - timedelta(days=60)
        )
    elif filtro == '60a90':
        facturas = facturas.filter(
            fecha_vencimiento__lte=hoy - timedelta(days=60),
            fecha_vencimiento__gt=hoy - timedelta(days=90)
        )
    elif filtro == '90a180':
        facturas = facturas.filter(
            fecha_vencimiento__lte=hoy - timedelta(days=90),
            fecha_vencimiento__gt=hoy - timedelta(days=180)
        )
    elif filtro == 'mas180':
        facturas = facturas.filter(fecha_vencimiento__lte=hoy - timedelta(days=180))

    # Días de atraso
    for f in facturas:
        f.dias_vencidos = (hoy - f.fecha_vencimiento).days
    

    return render(request, 'facturacion/cartera_vencida.html', {
        'facturas': facturas,
        'hoy': hoy,
        'empresas': Empresa.objects.all(),
        'clientes': Cliente.objects.all(),
        'rango_seleccionado': filtro
    })

@login_required
def exportar_cartera_excel(request):
    hoy = timezone.now().date()
    facturas = Factura.objects.filter(
        estatus='pendiente',
        fecha_vencimiento__lt=hoy,
        activo=True
    )

    if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
        facturas = facturas.filter(empresa=request.user.perfilusuario.empresa)

    # Crear libro y hoja
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cartera Vencida"

    # Encabezados
    ws.append([
        'Folio', 'Cliente', 'Empresa', 'Local/Área', 'Monto',
        'Saldo Pendiente', 'Fecha Vencimiento', 'Días Vencidos'
    ])

    # Contenido
    for factura in facturas:
        dias_vencidos = (hoy - factura.fecha_vencimiento).days
        origen = f"Local {factura.local.numero}" if factura.local else f"Área {factura.area_comun.numero}" if factura.area_comun else "-"
        ws.append([
            factura.folio,
            factura.cliente.nombre,
            factura.empresa.nombre,
            origen,
            float(factura.monto),
            float(factura.saldo_pendiente),
            str(factura.fecha_vencimiento),
            dias_vencidos
        ])

    # Respuesta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=cartera_vencida.xlsx'
    wb.save(response)
    return response

@login_required
def exportar_pagos_excel(request):
    pagos = Pago.objects.select_related('factura', 'registrado_por').all()

    # Si el usuario no es superusuario, filtra por su empresa
    if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
        pagos = pagos.filter(factura__empresa=request.user.perfilusuario.empresa)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pagos"

    # Encabezados
    ws.append([
        'Factura (Folio)',
        'Empresa',
        'Cliente',
        'Monto del Pago',
        'Fecha de Pago',
        'Forma de Pago',
        'Registrado por'
        'Origen (Local/Área)'
    ])

    # Contenido
    for pago in pagos:
        factura = pago.factura
        empresa = factura.empresa.nombre
        cliente = factura.cliente.nombre
        origen = ''
        if pago.factura.local:
            origen = f"Local {pago.factura.local.numero}"
        elif pago.factura.area_comun:   
            origen = f"Área {pago.factura.area_comun.numero}"
        ws.append([
            factura.folio,
            empresa,
            cliente,
            float(pago.monto),
            pago.fecha_pago.strftime('%Y-%m-%d'),
            pago.forma_pago,
            pago.registrado_por.get_full_name() if pago.registrado_por else '—',
            origen  
        ])

    # Respuesta
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=pagos.xlsx'
    wb.save(response)
    return response