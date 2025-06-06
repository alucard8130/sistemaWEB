
# Create your views here.
from django.shortcuts import render, redirect,get_object_or_404
from areas.models import AreaComun
from clientes.models import Cliente
from empresas.models import Empresa
from locales.models import LocalComercial
from .forms import FacturaEditForm, FacturaForm, PagoForm,FacturaCargaMasivaForm
from .models import Factura, FacturaAuditoria, Pago
from django.utils.timezone import now
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from datetime import date, timedelta
from django.db.models import F, OuterRef, Subquery, Sum, DecimalField, Value, ExpressionWrapper
from django.db.models.functions import Coalesce
import openpyxl
from django.http import HttpResponse
from django.db.models import Q
from facturacion.models import Pago
from decimal import Decimal
from unidecode import unidecode
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime
from django.db.models import Sum
from django.db import transaction



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

            # Crea log por cada campo
            for field in form.fields:
                valor = getattr(factura, field)
                FacturaAuditoria.objects.create(
                    factura=factura,
                    usuario=request.user,
                    campo=field,
                    valor_anterior='--CREADA--',
                    valor_nuevo=valor
                )

            return redirect('lista_facturas')
    else:
        form = FacturaForm(user=request.user)

    return render(request, 'facturacion/crear_factura.html', {'form': form})


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

@login_required
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
@transaction.atomic
def registrar_pago(request, factura_id):
    factura = get_object_or_404(Factura, pk=factura_id)

    if factura.estatus == 'pagada' or factura.saldo_pendiente <= 0:
        messages.warning(request, "La factura ya está completamente pagada. No se pueden registrar más pagos.")
        return redirect('lista_facturas')

    if request.method == 'POST':
        form = PagoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.factura = factura           # SIEMPRE antes de save()
            pago.registrado_por = request.user

            if pago.forma_pago == 'nota_credito':
                pago.save()
                factura.estatus = 'cancelada'
                factura.save()
                messages.success(request, "La factura ha sido cancelada por nota de crédito.")
                return redirect('lista_facturas')

            if pago.monto > factura.saldo_pendiente:
                form.add_error('monto', f"El monto excede el saldo pendiente (${factura.saldo_pendiente:.2f}).")
            else:
                pago.save()
                pagos_validos = factura.pagos.exclude(forma_pago='nota_credito')
                total_pagado = sum([p.monto for p in pagos_validos])
                if total_pagado >= factura.monto:
                    factura.estatus = 'pagada'
                else:
                    factura.estatus = 'pendiente'
                factura.save()
                messages.success(request, f"Pago registrado. Saldo restante: ${factura.saldo_pendiente:.2f}")
                return redirect('lista_facturas')
    else:
        form = PagoForm()

    return render(request, 'facturacion/registrar_pago.html', {
        'form': form,
        'factura': factura,
        'saldo': factura.saldo_pendiente,
    })


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

    #total_pagos = pagos.aggregate(total=Sum('monto'))['total'] or 0
    # Solo pagos válidos (excluyendo nota de crédito)
    pagos_validos = pagos.exclude(forma_pago='nota_credito')
    #pagos_validos = Pago.objects.filter(factura=Factura).exclude(forma_pago='nota_credito')
    total_pagos = pagos_validos.aggregate(total=Sum('monto'))['total'] or 0

    return render(request, 'facturacion/pagos_por_origen.html', {
        'pagos': pagos,
        'tipo': tipo,
        'total_pagos': total_pagos,
    })

@login_required
def dashboard_saldos(request):
    hoy = timezone.now().date()
    cliente_id = request.GET.get('cliente')
    origen = request.GET.get('origen')
    es_super = request.user.is_superuser

    # Empresa según usuario
    if es_super:
        empresas = Empresa.objects.all()
        empresa_id = request.GET.get('empresa')
        if not empresa_id or empresa_id == "todas":
            filtro_empresa = Q()
        else:
            filtro_empresa = Q(empresa_id=empresa_id)
    else:
        empresa = request.user.perfilusuario.empresa
        empresas = Empresa.objects.filter(id=empresa.id)
        empresa_id = empresa.id
        filtro_empresa = Q(empresa_id=empresa_id)

    # Filtrado base de facturas pendientes
    facturas = Factura.objects.filter(estatus='pendiente').filter(filtro_empresa)
    if cliente_id:
        facturas = facturas.filter(cliente_id=cliente_id)
    if origen == 'local':
        facturas = facturas.filter(local__isnull=False)
    elif origen == 'area':
        facturas = facturas.filter(area_comun__isnull=False)

    # Subconsulta: total pagado por factura
    pagos_subquery = Pago.objects.filter(factura=OuterRef('pk')) \
        .values('factura') \
        .annotate(total_pagado_dash=Coalesce(Sum('monto'), Value(0, output_field=DecimalField()))) \
        .values('total_pagado_dash')
    facturas = facturas.annotate(
        total_pagado_dash=Coalesce(Subquery(pagos_subquery), Value(0, output_field=DecimalField())),
        saldo_pendiente_dash=ExpressionWrapper(
            F('monto') - Coalesce(Subquery(pagos_subquery), Value(0, output_field=DecimalField())),
            output_field=DecimalField()
        )
    )

    # Saldos por grupo de vencimiento (puedes cambiar los días según tu lógica)
    saldo_0_30 = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=30)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_31_60 = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=60), fecha_vencimiento__lte=hoy - timedelta(days=30)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_61_90 = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=90), fecha_vencimiento__lte=hoy - timedelta(days=60)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_91_180 = facturas.filter(fecha_vencimiento__gt=hoy - timedelta(days=180), fecha_vencimiento__lte=hoy - timedelta(days=90)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0
    saldo_181_mas = facturas.filter(fecha_vencimiento__lte=hoy - timedelta(days=180)).aggregate(total=Sum('saldo_pendiente_dash'))['total'] or 0

    clientes = Cliente.objects.filter(empresa__in=empresas)

    return render(request, 'dashboard/saldos.html', {
        'facturas': facturas,
        'clientes': clientes,
        'empresas': empresas,
        'empresa_id': str(empresa_id) if empresa_id else "",
        'cliente_id': int(cliente_id) if cliente_id else None,
        'saldo_0_30': saldo_0_30,
        'saldo_31_60': saldo_31_60,
        'saldo_61_90': saldo_61_90,
        'saldo_91_180': saldo_91_180,
        'saldo_181_mas': saldo_181_mas,
        'origen': origen,
        'es_super': es_super,
    })

@login_required
def dashboard_pagos(request):
    es_super = request.user.is_superuser

    if es_super:
        empresas = Empresa.objects.all()
        empresa_id = request.GET.get('empresa')
        if not empresa_id or empresa_id == "todas":
            filtro_empresa = Q()
        else:
            filtro_empresa = Q(factura__empresa_id=empresa_id)
    else:
        empresa = request.user.perfilusuario.empresa
        empresas = Empresa.objects.filter(id=empresa.id)
        empresa_id = empresa.id
        filtro_empresa = Q(factura__empresa_id=empresa_id)

    cliente_id = request.GET.get('cliente')
    origen = request.GET.get('origen')
    anio = request.GET.get('anio')
    mes = request.GET.get('mes')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    filtro = Q(factura__activo=True) & filtro_empresa

    if cliente_id:
        filtro &= Q(factura__cliente_id=cliente_id)
    if origen == 'local':
        filtro &= Q(factura__local__isnull=False)
    elif origen == 'area':
        filtro &= Q(factura__area_comun__isnull=False)

    #pagos = Pago.objects.filter(filtro)
    pagos = Pago.objects.exclude(forma_pago='nota_credito').aggregate(total=Sum('monto'))['total'] or 0


    # Filtros de fechas
    if anio:
        pagos = pagos.filter(fecha_pago__year=anio)
    if mes:
        pagos = pagos.filter(fecha_pago__month=mes)
    if fecha_inicio and fecha_fin:
        try:
            # Valida fechas
            fecha_i = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_f = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            pagos = pagos.filter(fecha_pago__range=[fecha_i, fecha_f])
        except:
            pass

    # Pagos por mes para el gráfico
    #pagos_por_mes = pagos.annotate(mes=TruncMonth('fecha_pago')).values('mes').annotate(total=Sum('monto')).order_by('mes')

    pagos_por_mes = pagos.annotate(mes=TruncMonth('fecha_pago')).values('mes').annotate(total=Sum('monto')).order_by('mes')
    pagos_por_anio = pagos.annotate(anio=TruncYear('fecha_pago')).values('anio').annotate(total=Sum('monto')).order_by('anio')

    clientes = Cliente.objects.filter(empresa__in=empresas)

    return render(request, 'dashboard/pagos.html', {
        'pagos': pagos,
        'empresas': empresas,
        'empresa_id': str(empresa_id) if empresa_id else "",
        'clientes': clientes,
        'cliente_id': int(cliente_id) if cliente_id else None,
        'origen': origen,
        'es_super': es_super,
        #'pagos_por_mes': pagos_por_mes,
        'pagos_por_mes': pagos_por_mes,
        'pagos_por_anio': pagos_por_anio,
        'anio': anio,
        'mes': mes,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })


@login_required
def cartera_vencida(request):
    hoy = timezone.now().date()
    filtro = request.GET.get('rango')
    origen = request.GET.get('origen')

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

    # Filtrar por origen (local o área)
    if origen == 'local':
        facturas = facturas.filter(local__isnull=False)
    elif origen == 'area':
        facturas = facturas.filter(area_comun__isnull=False)

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
        
    origen = request.GET.get('origen')
    if origen == 'local':
        facturas = facturas.filter(local__isnull=False)
    elif origen == 'area':
        facturas = facturas.filter(area_comun__isnull=False)

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


def buscar_por_id_o_nombre(modelo, valor, campo='nombre'):
    """Busca por ID, si falla busca por nombre (sin acentos, insensible a mayúsculas). Reporta conflicto si hay varias."""
    if not valor:
        return None
    val = str(valor).strip().replace(',', '')
    try:
        return modelo.objects.get(pk=int(val))
    except (ValueError, modelo.DoesNotExist):
        todos = modelo.objects.all()
        # Lista de coincidencias insensibles a acentos y mayúsculas
        candidatos = [
            obj for obj in todos
            if unidecode(val).lower() in unidecode(str(getattr(obj, campo))).lower()
        ]
        if len(candidatos) == 1:
            return candidatos[0]
        elif len(candidatos) > 1:
            conflicto = "; ".join([f"ID={obj.pk}, {campo}='{getattr(obj, campo)}'" for obj in candidatos])
            raise Exception(f"Conflicto: '{valor}' coincide con varios registros en {modelo.__name__}: {conflicto}")
        raise Exception(f"No se encontró '{valor}' en {modelo.__name__}")


@staff_member_required
def carga_masiva_facturas(request):
    if request.method == 'POST':
        form = FacturaCargaMasivaForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
            errores = []
            COLUMNAS_ESPERADAS = 9  # Cambia según tus columnas
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if row is None:
                    continue
                if len(row) != COLUMNAS_ESPERADAS:
                    errores.append(f"Fila {i}: número de columnas incorrecto ({len(row)} en vez de {COLUMNAS_ESPERADAS})")
                    continue
                folio, empresa_val, cliente_val, local_val, area_val, monto, fecha_emision, fecha_vencimiento, observaciones = row
                try:
                    empresa = buscar_por_id_o_nombre(Empresa, empresa_val)
                    cliente = buscar_por_id_o_nombre(Cliente, cliente_val)
                    local = buscar_por_id_o_nombre(LocalComercial, local_val, campo='numero') if local_val else None
                    area = buscar_por_id_o_nombre(AreaComun, area_val, campo='numero') if area_val else None

                    Factura.objects.create(
                        folio=str(folio),
                        empresa=empresa,
                        cliente=cliente,
                        local=local,
                        area_comun=area,
                        monto=Decimal(monto),
                        fecha_emision=fecha_emision,
                        fecha_vencimiento=fecha_vencimiento,
                        observaciones=observaciones or "",
                    )
                except Exception as e:
                    errores.append(f"Fila {i}: {e}")

            if errores:
                messages.error(request, "Algunas facturas no se cargaron:<br>" + "<br>".join(errores))
            else:
                messages.success(request, "¡Facturas cargadas exitosamente!")
            return redirect('carga_masiva_facturas')
    else:
        form = FacturaCargaMasivaForm()
    return render(request, 'facturacion/carga_masiva_facturas.html', {'form': form})


@staff_member_required
def plantilla_facturas_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plantilla Facturas"

    # Encabezados (ajusta según tu modelo)
    ws.append([
        'folio', 'empresa_id', 'cliente_id', 'local_id', 'area_id', 'monto', 
        'fecha_emision', 'fecha_vencimiento', 'observaciones'
    ])
    # Fila de ejemplo (puedes poner valores ficticios)
    ws.append([
        'FAC001', 'Torre Reforma', 'Juan Pérez', 'L-101', '', '1500.00', '2025-06-10', '2025-07-10', 'Cuota mensual'
    ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_facturas.xlsx'
    wb.save(response)
    return response        

@login_required
def editar_factura(request, factura_id):
    factura = get_object_or_404(Factura, pk=factura_id)
    
     # Bloqueo si la factura está pagada
    if factura.estatus == 'pagada':
        messages.warning(request, "Esta factura ya está pagada y no puede ser editada.")
        return redirect('lista_facturas')    

    if request.method == 'POST':
        form = FacturaEditForm(request.POST, instance=factura)
        if form.is_valid():
            factura_original = Factura.objects.get(pk=factura_id)
            factura_modificada = form.save(commit=False)

            # Comparar y guardar auditoría
            for field in form.changed_data:
                valor_anterior = getattr(factura_original, field)
                valor_nuevo = getattr(factura_modificada, field)
                if str(valor_anterior) != str(valor_nuevo):
                    FacturaAuditoria.objects.create(
                        factura=factura,
                        usuario=request.user,
                        campo=field,
                        valor_anterior=valor_anterior,
                        valor_nuevo=valor_nuevo
                    )
            factura_modificada.save()
            return redirect('lista_facturas')
    else:
        form = FacturaEditForm(instance=factura)
    # Opcional: mostrar historial de auditoría de esta factura
    auditorias = FacturaAuditoria.objects.filter(factura=factura).order_by('-fecha')
    return render(request, 'facturacion/editar_factura.html', {
        'form': form,
        'factura': factura,
        'auditorias': auditorias,
    })