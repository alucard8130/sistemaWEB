from django.shortcuts import render
from django.db.models import Sum
from facturacion.models import Pago
from gastos.models import Gasto
from empresas.models import Empresa
from collections import OrderedDict
from django.db.models import Case, When, Value, CharField
import calendar
import datetime
import locale

def reporte_ingresos_vs_gastos(request):
    empresas = Empresa.objects.all()
    empresa_id = request.GET.get('empresa')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    mes= request.GET.get('mes')
    anio= request.GET.get('anio')
    periodo= request.GET.get('periodo')

    hoy = datetime.date.today()
    if not periodo and not fecha_inicio and not fecha_fin:
        periodo = 'mes_actual'

    if periodo == 'mes_actual':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (hoy.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    elif periodo == 'periodo_actual':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy  # <-- Hasta hoy, no hasta el 31 de diciembre
    elif fecha_inicio and fecha_fin:
        # Ya vienen del formulario
        pass
    else:
        fecha_inicio = None
        fecha_fin = None
    
    # Convierte a date si es string
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio_dt = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        except Exception:
            fecha_inicio_dt = None
    else:
        fecha_inicio_dt = fecha_inicio

    if isinstance(fecha_fin, str):
        try:
            fecha_fin_dt = datetime.datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        except Exception:
            fecha_fin_dt = None
    else:
        fecha_fin_dt = fecha_fin

    # Para mostrar el mes y año en letras
    import locale
    try:
        locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
    except:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    mes_letra = ""
    if fecha_inicio_dt and fecha_fin_dt and fecha_inicio_dt == fecha_fin_dt.replace(day=1):
        mes_letra = fecha_inicio_dt.strftime('%B %Y').capitalize()
    elif fecha_inicio_dt and fecha_fin_dt:
        mes_letra = f"{fecha_inicio_dt.strftime('%d/%m/%Y')} al {fecha_fin_dt.strftime('%d/%m/%Y')}"

    pagos = Pago.objects.exclude(forma_pago='nota_credito')
    gastos = Gasto.objects.all()

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        gastos = gastos.filter(empresa_id=empresa_id)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        gastos = gastos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        gastos = gastos.filter(fecha__lte=fecha_fin)

    total_ingresos = pagos.aggregate(total=Sum('monto'))['total'] or 0
    total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or 0

    # Agrupar por tipo de origen (Local/Área)
    ingresos_qs = pagos.annotate(
        origen=Case(
            When(factura__local__isnull=False, then=Value('Locales')),
            When(factura__area_comun__isnull=False, then=Value('Áreas Comunes')),
            default=Value('Sin origen'),
            output_field=CharField()
        )
    ).values('origen').annotate(total=Sum('monto')).order_by('origen')

    ingresos_por_origen = OrderedDict()
    for x in ingresos_qs:
        ingresos_por_origen[x['origen']] = float(x['total'])

    return render(request, 'informes_financieros/ingresos_vs_gastos.html', {
        'empresas': empresas,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'empresa_id': empresa_id,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'ingresos_por_origen': ingresos_por_origen,
        'periodo': periodo,
        'mes_letra': mes_letra,
    })

# Create your views here.
