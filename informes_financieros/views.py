from django.shortcuts import render
from django.db.models import Sum
from facturacion.models import CobroOtrosIngresos, Factura, FacturaOtrosIngresos, Pago
from gastos.models import Gasto, PagoGasto
from empresas.models import Empresa
from collections import OrderedDict
from django.db.models import Case, When, Value, CharField
import calendar
import datetime
import locale
from django.contrib.auth.decorators import login_required
from openpyxl import Workbook
from django.http import HttpResponse


@login_required
def reporte_ingresos_vs_gastos(request):
    empresas = Empresa.objects.all()
    empresa_id = request.GET.get("empresa")
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    periodo = request.GET.get("periodo")

    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or ""

    # Si no hay ningún filtro, mostrar periodo actual por default
    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = "periodo_actual"

    hoy = datetime.date.today()
    # Prioridad: periodo > mes/año > fechas manuales
    if periodo == "mes_actual":
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (hoy.replace(day=1) + datetime.timedelta(days=32)).replace(
            day=1
        ) - datetime.timedelta(days=1)
        mes = hoy.month
        anio = hoy.year
    elif periodo == "periodo_actual":
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy
        mes = ""
        anio = ""
    elif mes and anio:
        try:
            mes = int(mes)
            anio = int(anio)
            fecha_inicio = datetime.date(anio, mes, 1)
            if mes == 12:
                fecha_fin = datetime.date(anio, 12, 31)
            else:
                fecha_fin = datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            fecha_inicio = None
            fecha_fin = None
    elif fecha_inicio and fecha_fin:
        # Ya vienen del formulario
        pass
    else:
        fecha_inicio = None
        fecha_fin = None

    # Convierte a date si es string
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio_dt = datetime.datetime.strptime(
                fecha_inicio, "%Y-%m-%d"
            ).date()
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
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
    except:
        locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")

    mes_letra = ""
    if (
        fecha_inicio_dt
        and fecha_fin_dt
        and fecha_inicio_dt == fecha_fin_dt.replace(day=1)
    ):
        mes_letra = fecha_inicio_dt.strftime("%B %Y").capitalize()
    elif fecha_inicio_dt and fecha_fin_dt:
        mes_letra = f"{fecha_inicio_dt.strftime('%d/%m/%Y')} al {fecha_fin_dt.strftime('%d/%m/%Y')}"

    pagos = Pago.objects.exclude(forma_pago="nota_credito")
    gastos = Gasto.objects.all()
    cobros_otros = CobroOtrosIngresos.objects.select_related(
        "factura", "factura__empresa"
    )

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        gastos = gastos.filter(empresa_id=empresa_id)
        cobros_otros = cobros_otros.filter(factura__empresa_id=empresa_id)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        gastos = gastos.filter(fecha__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        gastos = gastos.filter(fecha__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)

    total_ingresos = pagos.aggregate(total=Sum("monto"))["total"] or 0
    total_otros_ingresos = cobros_otros.aggregate(total=Sum("monto"))["total"] or 0
    total_ingresos_cobrados = total_ingresos + total_otros_ingresos
    #total_gastos = gastos.aggregate(total=Sum("monto"))["total"] or 0
    total_gastos = gastos.filter(estatus='pagada').aggregate(total=Sum("monto"))["total"] or 0

    # Agrupar por tipo de origen (Local/Área)
    ingresos_qs = (
        pagos.annotate(
            origen=Case(
                When(factura__local__isnull=False, then=Value("Locales")),
                When(factura__area_comun__isnull=False, then=Value("Áreas Comunes")),
                default=Value("Sin origen"),
                output_field=CharField(),
            )
        )
        .values("origen")
        .annotate(total=Sum("monto"))
        .order_by("origen")
    )

    otros_ingresos_qs = (
        cobros_otros.values("factura__tipo_ingreso")
        .annotate(total=Sum("monto"))
        .order_by("factura__tipo_ingreso")
    )

    # Agrupar gastos por tipo
    gastos_por_tipo_qs = (
        gastos.values("tipo_gasto__nombre")
        .annotate(total=Sum("monto"))
        .order_by("tipo_gasto__nombre")
    )
    gastos_por_tipo = []
    for x in gastos_por_tipo_qs:
        gastos_por_tipo.append(
            {"tipo": x["tipo_gasto__nombre"] or "Sin tipo", "total": float(x["total"])}
        )

    # Crear un diccionario ordenado para los ingresos por origen
    ingresos_por_origen = OrderedDict()
    for x in ingresos_qs:
        ingresos_por_origen[x["origen"]] = float(x["total"])
    for x in otros_ingresos_qs:
        tipo = x["factura__tipo_ingreso"] or "Otros ingresos"
        ingresos_por_origen[f" {tipo}"] = float(x["total"])

    saldo = total_ingresos_cobrados - total_gastos

    return render(
        request,
        "informes_financieros/ingresos_vs_gastos.html",
        {
            "empresas": empresas,
            "total_ingresos": total_ingresos_cobrados,
            "total_otros_ingresos": total_otros_ingresos,
            "total_gastos": total_gastos,
            "empresa_id": empresa_id,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "ingresos_por_origen": ingresos_por_origen,
            "periodo": periodo,
            "mes_letra": mes_letra,
            "mes": mes,
            "anio": anio,
            "gastos_por_tipo": gastos_por_tipo,
            "saldo": saldo,

        },
    )


@login_required
def estado_resultados(request):
    empresas = Empresa.objects.all()
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    periodo = request.GET.get("periodo")
    modo = request.GET.get('modo', 'flujo')
    hoy = datetime.date.today()

    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or ""

    pagos = Pago.objects.exclude(forma_pago="nota_credito")
    cobros_otros = CobroOtrosIngresos.objects.select_related("factura", "factura__empresa")
    gastos = Gasto.objects.all()

    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = "periodo_actual"

    if periodo == "periodo_actual":
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy
        mes = ""
        anio = ""

    if mes and anio:
        try:
            mes = int(mes)
            anio = int(anio)
            fecha_inicio = datetime.date(anio, mes, 1)
            if mes == 12:
                fecha_fin = datetime.date(anio, 12, 31)
            else:
                fecha_fin = datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            fecha_inicio = None
            fecha_fin = None

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        cobros_otros = cobros_otros.filter(factura__empresa_id=empresa_id)
        gastos = gastos.filter(empresa_id=empresa_id)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
        gastos = gastos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)
        gastos = gastos.filter(fecha__lte=fecha_fin)

    if modo == 'flujo':
        pagos_modo = pagos
        cobros_otros_modo = cobros_otros
        gastos_modo = PagoGasto.objects.filter(fecha_pago__range=[fecha_inicio, fecha_fin])
        if empresa_id:
            gastos_modo = gastos_modo.filter(gasto__empresa_id=empresa_id)
        ingresos_qs = (
            pagos_modo.annotate(
                origen=Case(
                    When(factura__local__isnull=False, then=Value("Locales")),
                    When(factura__area_comun__isnull=False, then=Value("Áreas Comunes")),
                    default=Value("Sin origen"),
                    output_field=CharField(),
                )
            )
            .values("origen")
            .annotate(total=Sum("monto"))
            .order_by("origen")
        )
        otros_ingresos_qs = (
            cobros_otros_modo.values("factura__tipo_ingreso")
            .annotate(total=Sum("monto"))
            .order_by("factura__tipo_ingreso")
        )
        ingresos_por_origen = OrderedDict()
        for x in ingresos_qs:
            ingresos_por_origen[x["origen"]] = float(x["total"])
        for x in otros_ingresos_qs:
            tipo = x["factura__tipo_ingreso"] or "Otros ingresos"
            ingresos_por_origen[f"Otros ingresos - {tipo}"] = float(x["total"])
        total_ingresos = float(sum(ingresos_por_origen.values()))
        gastos_por_grupo = (
            gastos_modo.values(
                "gasto__tipo_gasto__subgrupo__grupo__nombre",
                "gasto__tipo_gasto__subgrupo__nombre",
                "gasto__tipo_gasto__nombre"
            )
            .annotate(total=Sum("monto"))
            .order_by("gasto__tipo_gasto__subgrupo__grupo__nombre", "gasto__tipo_gasto__subgrupo__nombre", "gasto__tipo_gasto__nombre")
        )
        gastos_por_tipo_qs = (
            gastos_modo.values("gasto__tipo_gasto__nombre")
            .annotate(total=Sum("monto"))
            .order_by("gasto__tipo_gasto__nombre")
        )
    else:
        facturas_cuotas = Factura.objects.filter(
            fecha_vencimiento__range=[fecha_inicio, fecha_fin]
        )
        facturas_otros = FacturaOtrosIngresos.objects.filter(
            fecha_vencimiento__range=[fecha_inicio, fecha_fin]
        )
        if empresa_id:
            facturas_cuotas = facturas_cuotas.filter(empresa_id=empresa_id)
            facturas_otros = facturas_otros.filter(empresa_id=empresa_id)
        ingresos_por_origen = OrderedDict()
        origenes = facturas_cuotas.annotate(
            origen=Case(
                When(local__isnull=False, then=Value("Locales")),
                When(area_comun__isnull=False, then=Value("Áreas Comunes")),
                default=Value("Sin origen"),
                output_field=CharField(),
            )
        ).values("origen").annotate(total=Sum("monto")).order_by("origen")
        for x in origenes:
            ingresos_por_origen[x["origen"]] = float(x["total"])
        otros = facturas_otros.values("tipo_ingreso").annotate(total=Sum("monto")).order_by("tipo_ingreso")
        for x in otros:
            tipo = x["tipo_ingreso"] or "Otros ingresos"
            ingresos_por_origen[f"Otros ingresos - {tipo}"] = float(x["total"])
        total_ingresos = float(sum(ingresos_por_origen.values()))
        gastos_por_grupo = (
            gastos.values(
                "tipo_gasto__subgrupo__grupo__nombre",
                "tipo_gasto__subgrupo__nombre",
                "tipo_gasto__nombre"
            )
            .annotate(total=Sum("monto"))
            .order_by("tipo_gasto__subgrupo__grupo__nombre", "tipo_gasto__subgrupo__nombre", "tipo_gasto__nombre")
        )
        gastos_por_tipo_qs = (
            gastos.values("tipo_gasto__nombre")
            .annotate(total=Sum("monto"))
            .order_by("tipo_gasto__nombre")
        )

    # Estructura anidada: grupo > subgrupo > tipos
    estructura_gastos = OrderedDict()
    for g in gastos_por_grupo:
        if modo == 'flujo':
            grupo = g["gasto__tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo"
            subgrupo = g["gasto__tipo_gasto__subgrupo__nombre"] or "Sin subgrupo"
            tipo = g["gasto__tipo_gasto__nombre"] or "Sin tipo"
        else:
            grupo = g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo"
            subgrupo = g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo"
            tipo = g["tipo_gasto__nombre"] or "Sin tipo"
        total = float(g["total"])
        if grupo not in estructura_gastos:
            estructura_gastos[grupo] = OrderedDict()
        if subgrupo not in estructura_gastos[grupo]:
            estructura_gastos[grupo][subgrupo] = []
        estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})

    gastos_por_tipo = []
    for x in gastos_por_tipo_qs:
        if modo == 'flujo':
            nombre_tipo = x["gasto__tipo_gasto__nombre"]
        else:
            nombre_tipo = x["tipo_gasto__nombre"]
        gastos_por_tipo.append(
            {"tipo": nombre_tipo or "Sin tipo", "total": float(x["total"])}
        )

    total_gastos = float(sum(g["total"] for g in gastos_por_tipo))
    saldo = float(total_ingresos - total_gastos)

    return render(
        request,
        "informes_financieros/estado_resultados.html",
        {
            "empresas": empresas,
            "ingresos_por_origen": ingresos_por_origen,
            "gastos_por_tipo": gastos_por_tipo,
            "estructura_gastos": estructura_gastos,
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "saldo": saldo,
            "empresa_id": str(empresa_id or ""),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "mes": str(mes or ""),
            "anio": str(anio or ""),
            "periodo": periodo,
            "modo": modo,
        },
    )

@login_required
def exportar_estado_resultados_excel(request):
    empresas = Empresa.objects.all()
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    periodo = request.GET.get("periodo")
    modo = request.GET.get('modo', 'flujo')
    hoy = datetime.date.today()

    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or ""

    pagos = Pago.objects.exclude(forma_pago="nota_credito")
    cobros_otros = CobroOtrosIngresos.objects.select_related("factura", "factura__empresa")
    gastos = Gasto.objects.all()

    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = "periodo_actual"

    if periodo == "periodo_actual":
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy
        mes = ""
        anio = ""

    if mes and anio:
        try:
            mes = int(mes)
            anio = int(anio)
            fecha_inicio = datetime.date(anio, mes, 1)
            if mes == 12:
                fecha_fin = datetime.date(anio, 12, 31)
            else:
                fecha_fin = datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            fecha_inicio = None
            fecha_fin = None

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        cobros_otros = cobros_otros.filter(factura__empresa_id=empresa_id)
        gastos = gastos.filter(empresa_id=empresa_id)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
        gastos = gastos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)
        gastos = gastos.filter(fecha__lte=fecha_fin)

    # --- AJUSTE SEGÚN MODO ---
    if modo == 'flujo':
        pagos_modo = pagos
        cobros_otros_modo = cobros_otros
        gastos_modo = PagoGasto.objects.filter(fecha_pago__range=[fecha_inicio, fecha_fin])
        # Ingresos por origen
        ingresos_qs = (
            pagos_modo.annotate(
                origen=Case(
                    When(factura__local__isnull=False, then=Value("Locales")),
                    When(factura__area_comun__isnull=False, then=Value("Áreas Comunes")),
                    default=Value("Sin origen"),
                    output_field=CharField(),
                )
            )
            .values("origen")
            .annotate(total=Sum("monto"))
            .order_by("origen")
        )
        otros_ingresos_qs = (
            cobros_otros_modo.values("factura__tipo_ingreso")
            .annotate(total=Sum("monto"))
            .order_by("factura__tipo_ingreso")
        )
        ingresos_por_origen = []
        for x in ingresos_qs:
            ingresos_por_origen.append((x["origen"], float(x["total"])))
        for x in otros_ingresos_qs:
            tipo = x["factura__tipo_ingreso"] or "Otros ingresos"
            ingresos_por_origen.append((f"Otros ingresos - {tipo}", float(x["total"])))
        total_ingresos = float(sum(x[1] for x in ingresos_por_origen))
        # Gastos agrupados por grupo, subgrupo y tipo (usando PagoGasto)
        gastos_por_grupo = (
            gastos_modo.values(
                "gasto__tipo_gasto__subgrupo__grupo__nombre",
                "gasto__tipo_gasto__subgrupo__nombre",
                "gasto__tipo_gasto__nombre"
            )
            .annotate(total=Sum("monto"))
            .order_by("gasto__tipo_gasto__subgrupo__grupo__nombre", "gasto__tipo_gasto__subgrupo__nombre", "gasto__tipo_gasto__nombre")
        )
        # Estructura anidada
        estructura_gastos = OrderedDict()
        for g in gastos_por_grupo:
            grupo = g["gasto__tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo"
            subgrupo = g["gasto__tipo_gasto__subgrupo__nombre"] or "Sin subgrupo"
            tipo = g["gasto__tipo_gasto__nombre"] or "Sin tipo"
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        total_gastos = float(sum(g["total"] for g in gastos_por_grupo))
    else:
        # Modo resultados (usa facturas, no pagos)
        facturas_cuotas = Factura.objects.filter(
            fecha_vencimiento__range=[fecha_inicio, fecha_fin]
        )
        facturas_otros = FacturaOtrosIngresos.objects.filter(
            fecha_vencimiento__range=[fecha_inicio, fecha_fin]
        )
        if empresa_id:
            facturas_cuotas = facturas_cuotas.filter(empresa_id=empresa_id)
            facturas_otros = facturas_otros.filter(empresa_id=empresa_id)
        ingresos_por_origen = []
        origenes = facturas_cuotas.annotate(
            origen=Case(
                When(local__isnull=False, then=Value("Locales")),
                When(area_comun__isnull=False, then=Value("Áreas Comunes")),
                default=Value("Sin origen"),
                output_field=CharField(),
            )
        ).values("origen").annotate(total=Sum("monto")).order_by("origen")
        for x in origenes:
            ingresos_por_origen.append((x["origen"], float(x["total"])))
        otros = facturas_otros.values("tipo_ingreso").annotate(total=Sum("monto")).order_by("tipo_ingreso")
        for x in otros:
            tipo = x["tipo_ingreso"] or "Otros ingresos"
            ingresos_por_origen.append((f"Otros ingresos - {tipo}", float(x["total"])))
        total_ingresos = float(sum(x[1] for x in ingresos_por_origen))
        gastos_por_grupo = (
            gastos.values(
                "tipo_gasto__subgrupo__grupo__nombre",
                "tipo_gasto__subgrupo__nombre",
                "tipo_gasto__nombre"
            )
            .annotate(total=Sum("monto"))
            .order_by("tipo_gasto__subgrupo__grupo__nombre", "tipo_gasto__subgrupo__nombre", "tipo_gasto__nombre")
        )
        estructura_gastos = OrderedDict()
        for g in gastos_por_grupo:
            grupo = g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo"
            subgrupo = g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo"
            tipo = g["tipo_gasto__nombre"] or "Sin tipo"
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        total_gastos = float(sum(g["total"] for g in gastos_por_grupo))

    saldo = float(total_ingresos) - float(total_gastos)

    # --- Generar Excel ---
    wb = Workbook()
    ws = wb.active
    ws.title = "Estado de Resultados"

    ws.append(["Estado de Resultados"])
    ws.append([])

    ws.append(["Ingresos"])
    for origen, monto in ingresos_por_origen:
        ws.append([origen, monto])
    ws.append(["Total Ingresos", total_ingresos])
    ws.append([])

    ws.append(["Gastos"])
    for grupo, subgrupos in estructura_gastos.items():
        ws.append([grupo])
        for subgrupo, tipos in subgrupos.items():
            ws.append(["", subgrupo])
            for tipo in tipos:
                ws.append(["", "", tipo["tipo"], tipo["total"]])
    ws.append(["Total Gastos", total_gastos])
    ws.append([])

    ws.append(["Resultado", saldo])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=estado_resultados.xlsx"
    wb.save(response)
    return response