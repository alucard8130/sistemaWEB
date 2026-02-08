from django.shortcuts import render

# from django.db.models import Sum
from caja_chica.models import FondeoCajaChica, GastoCajaChica, ValeCaja
from facturacion.models import CobroOtrosIngresos, Factura, FacturaOtrosIngresos, Pago
from gastos.models import Gasto, PagoGasto
from empresas.models import Empresa
from collections import OrderedDict

# from django.db.models import Case, When, Value, CharField
import calendar
import datetime
import locale
from django.contrib.auth.decorators import login_required
from openpyxl import Workbook
from django.http import HttpResponse
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from django.db.models import F, Value, CharField, Sum, Case, When, IntegerField


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

    try:
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
        except locale.Error:
            locale.setlocale(locale.LC_TIME, "C")  # Fallback seguro

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
    pagos_gastos = PagoGasto.objects.all()
    cobros_otros = CobroOtrosIngresos.objects.select_related(
        "factura", "factura__empresa"
    )
    gastos_caja_chica = GastoCajaChica.objects.all()
    vales_caja_chica = ValeCaja.objects.all()

    # PAGOS POR IDENTIFICAR
    pagos_por_identificar = Pago.objects.filter(
        factura__isnull=True, identificado=False
    )

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        pagos_gastos = pagos_gastos.filter(gasto__empresa_id=empresa_id)
        cobros_otros = cobros_otros.filter(factura__empresa_id=empresa_id)
        gastos_caja_chica = gastos_caja_chica.filter(fondeo__empresa_id=empresa_id)
        vales_caja_chica = vales_caja_chica.filter(fondeo__empresa_id=empresa_id)
        pagos_por_identificar = pagos_por_identificar.filter(empresa_id=empresa_id)
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        pagos_gastos = pagos_gastos.filter(fecha_pago__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__gte=fecha_inicio)
        vales_caja_chica = vales_caja_chica.filter(fecha__gte=fecha_inicio)
        pagos_por_identificar = pagos_por_identificar.filter(
            fecha_pago__gte=fecha_inicio
        )
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        pagos_gastos = pagos_gastos.filter(fecha_pago__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__lte=fecha_fin)
        vales_caja_chica = vales_caja_chica.filter(fecha__lte=fecha_fin)
        pagos_por_identificar = pagos_por_identificar.filter(fecha_pago__lte=fecha_fin)

    total_ingresos = pagos.aggregate(total=Sum("monto"))["total"] or 0
    total_otros_ingresos = cobros_otros.aggregate(total=Sum("monto"))["total"] or 0
    total_ingresos_cobrados = total_ingresos + total_otros_ingresos
    total_pagos_por_identificar = (
        pagos_por_identificar.aggregate(total=Sum("monto"))["total"] or 0
    )
    total_gastos_pagados = pagos_gastos.aggregate(total=Sum("monto"))["total"] or 0
    total_gastos_caja_chica = (
        gastos_caja_chica.aggregate(total=Sum("importe"))["total"] or 0
    )
    total_vales_caja_chica = (
        vales_caja_chica.aggregate(total=Sum("importe"))["total"] or 0
    )
    total_egresos = (
        total_gastos_pagados + total_gastos_caja_chica + total_vales_caja_chica
    )

    # Agrupar por tipo de origen (Local/Área)
    ingresos_qs = (
        pagos.annotate(
            origen=Case(
                When(factura__local__isnull=False, then=Value("Propiedades")),
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
        cobros_otros.select_related("factura__tipo_ingreso")
        .values("factura__tipo_ingreso__nombre")
        .annotate(total=Sum("monto"))
        .order_by("factura__tipo_ingreso")
    )

    # Agrupar y sumar todos los gastos por tipo (gastos normales, caja chica y vales)
    gastos_por_tipo_dict = {}
    # Gastos normales
    for g in pagos_gastos.values("gasto__tipo_gasto__nombre").annotate(
        total=Sum("monto")
    ):
        tipo = g["gasto__tipo_gasto__nombre"] or "Sin tipo"
        gastos_por_tipo_dict[tipo] = gastos_por_tipo_dict.get(tipo, 0) + float(
            g["total"]
        )
    # Caja chica
    for g in gastos_caja_chica.values("tipo_gasto__nombre").annotate(
        total=Sum("importe")
    ):
        tipo = g["tipo_gasto__nombre"] or "Sin tipo"
        gastos_por_tipo_dict[tipo] = gastos_por_tipo_dict.get(tipo, 0) + float(
            g["total"]
        )
    # Vales de caja chica agrupados por tipo real
    for g in vales_caja_chica.values("tipo_gasto__nombre").annotate(
        total=Sum("importe")
    ):
        tipo = g["tipo_gasto__nombre"] or "Sin tipo"
        gastos_por_tipo_dict[tipo] = gastos_por_tipo_dict.get(tipo, 0) + float(
            g["total"]
        )

    gastos_por_tipo = [
        {"tipo": tipo, "total": total} for tipo, total in gastos_por_tipo_dict.items()
    ]

    # Crear un diccionario ordenado para los ingresos por origen
    ingresos_por_origen = OrderedDict()
    for x in ingresos_qs:
        ingresos_por_origen[x["origen"]] = float(x["total"])
    for x in otros_ingresos_qs:
        tipo = x["factura__tipo_ingreso__nombre"] or "Otros ingresos"
        ingresos_por_origen[f" {tipo}"] = float(x["total"])
    ingresos_por_origen["Depositos no identificados"] = float(
        total_pagos_por_identificar
    )

    gastos_agregados = {}

    # Define gastos_qs similar to the commented-out section above
    gastos_qs = PagoGasto.objects.select_related("gasto__tipo_gasto__subgrupo__grupo")
    if empresa_id:
        gastos_qs = gastos_qs.filter(gasto__empresa_id=empresa_id)
    if fecha_inicio:
        gastos_qs = gastos_qs.filter(fecha_pago__gte=fecha_inicio)
    if fecha_fin:
        gastos_qs = gastos_qs.filter(fecha_pago__lte=fecha_fin)

    # Gastos normales
    for g in gastos_qs.values(
        "gasto__tipo_gasto__subgrupo__grupo__nombre",
        "gasto__tipo_gasto__subgrupo__nombre",
        "gasto__tipo_gasto__nombre",
    ).annotate(total=Sum("monto")):
        grupo = (
            (g["gasto__tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
            .strip()
            .title()
        )
        subgrupo = (
            (g["gasto__tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
        )
        tipo = (g["gasto__tipo_gasto__nombre"] or "Sin tipo").strip().title()
        key = (grupo, subgrupo, tipo)
        gastos_agregados[key] = gastos_agregados.get(key, 0) + float(g["total"])

    # Caja chica
    for g in gastos_caja_chica.values(
        "tipo_gasto__subgrupo__grupo__nombre",
        "tipo_gasto__subgrupo__nombre",
        "tipo_gasto__nombre",
    ).annotate(total=Sum("importe")):
        grupo = (
            (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo").strip().title()
        )
        subgrupo = (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
        tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
        key = (grupo, subgrupo, tipo)
        gastos_agregados[key] = gastos_agregados.get(key, 0) + float(g["total"])

    # Vales de caja chica
    for g in vales_caja_chica.values(
        "tipo_gasto__subgrupo__grupo__nombre",
        "tipo_gasto__subgrupo__nombre",
        "tipo_gasto__nombre",
    ).annotate(total=Sum("importe")):
        grupo = (
            (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo").strip().title()
        )
        subgrupo = (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
        tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
        key = (grupo, subgrupo, tipo)
        gastos_agregados[key] = gastos_agregados.get(key, 0) + float(g["total"])

    # Ahora arma la estructura final agrupada
    estructura_gastos = OrderedDict()
    for (grupo, subgrupo, tipo), total in gastos_agregados.items():
        if grupo not in estructura_gastos:
            estructura_gastos[grupo] = OrderedDict()
        if subgrupo not in estructura_gastos[grupo]:
            estructura_gastos[grupo][subgrupo] = []
        estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})

    saldo = total_ingresos_cobrados - total_egresos

    return render(
        request,
        "informes_financieros/ingresos_vs_gastos.html",
        {
            "empresas": empresas,
            "total_ingresos": total_ingresos_cobrados,
            "total_otros_ingresos": total_otros_ingresos,
            "total_pagos_por_identificar": total_pagos_por_identificar,
            "total_gastos_pagados": total_gastos_pagados,
            "total_gastos_caja_chica": total_gastos_caja_chica,
            "total_vales_caja_chica": total_vales_caja_chica,
            "total_egresos": total_egresos,
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
            "estructura_gastos": estructura_gastos,
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
    modo = request.GET.get("modo", "flujo")
    hoy = datetime.date.today()

    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or request.session.get("empresa_id")
        if not empresa_id or not str(empresa_id).isdigit():
            empresa_id = None

    # Obtener meses y años existentes en la base de datos
    if empresa_id:
        meses_anios = (
            Factura.objects.filter(empresa_id=empresa_id)
            .annotate(
                mes=ExtractMonth("fecha_vencimiento"),
                anio=ExtractYear("fecha_vencimiento"),
            )
            .values("mes", "anio")
            .distinct()
        )
        meses_anios_otros = (
            FacturaOtrosIngresos.objects.filter(empresa_id=empresa_id)
            .annotate(
                mes=ExtractMonth("fecha_vencimiento"),
                anio=ExtractYear("fecha_vencimiento"),
            )
            .values("mes", "anio")
            .distinct()
        )
    else:
        meses_anios = (
            Factura.objects.annotate(
                mes=ExtractMonth("fecha_vencimiento"),
                anio=ExtractYear("fecha_vencimiento"),
            )
            .values("mes", "anio")
            .distinct()
        )
        meses_anios_otros = (
            FacturaOtrosIngresos.objects.annotate(
                mes=ExtractMonth("fecha_vencimiento"),
                anio=ExtractYear("fecha_vencimiento"),
            )
            .values("mes", "anio")
            .distinct()
        )

    meses_anios_set = set(
        (x["mes"], x["anio"]) for x in list(meses_anios) + list(meses_anios_otros)
    )
    # Filtra tuplas donde mes o año sean None
    meses_anios_list = sorted(
        [t for t in meses_anios_set if t[0] is not None and t[1] is not None],
        key=lambda x: (x[1], x[0])
    )
    # meses_anios_list = sorted(list(meses_anios_set), key=lambda x: (x[1], x[0]))
    meses_unicos = sorted(set(m for m, y in meses_anios_list if m))
    anios_unicos = sorted(set(y for m, y in meses_anios_list if y))

    pagos = Pago.objects.exclude(forma_pago="nota_credito")
    cobros_otros = CobroOtrosIngresos.objects.select_related(
        "factura", "factura__empresa"
    )
    gastos = Gasto.objects.all()
    gastos_caja_chica = GastoCajaChica.objects.all()
    vales_caja_chica = ValeCaja.objects.all()


    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = "periodo_actual"

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
        pass
    else:
        fecha_inicio = None
        fecha_fin = None
    # Convierte a date si es string
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        except Exception:
            fecha_inicio_dt = None
    else:
        fecha_inicio_dt = fecha_inicio

    if isinstance(fecha_fin, str):
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        except Exception:
            fecha_fin_dt = None
    else:
        fecha_fin_dt = fecha_fin

    # Para mostrar el mes y año en letras
    try:
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
        except locale.Error:
            locale.setlocale(locale.LC_TIME, "C")  # Fallback seguro

    mes_letra = ""
    if (
        fecha_inicio_dt
        and fecha_fin_dt
        and fecha_inicio_dt == fecha_fin_dt.replace(day=1)
    ):
        mes_letra = fecha_inicio_dt.strftime("%B %Y").capitalize()
    elif fecha_inicio_dt and fecha_fin_dt:
        mes_letra = f"{fecha_inicio_dt.strftime('%d/%m/%Y')} al {fecha_fin_dt.strftime('%d/%m/%Y')}"

    empresa = None
    saldo_inicial = 0
    saldo_final = 0

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        cobros_otros = cobros_otros.filter(factura__empresa_id=empresa_id)
        gastos = gastos.filter(empresa_id=empresa_id)
        gastos_caja_chica = gastos_caja_chica.filter(fondeo__empresa_id=empresa_id)
        vales_caja_chica = vales_caja_chica.filter(fondeo__empresa_id=empresa_id)
    try:
        empresa = Empresa.objects.get(id=empresa_id)
        saldo_inicial = float(empresa.saldo_inicial or 0)
        saldo_final = float(empresa.saldo_final or 0)
    except Empresa.DoesNotExist:
        saldo_inicial = 0
        saldo_final = 0
    # --- FILTRO POR FECHA ---
    if fecha_inicio:
        gastos_caja_chica = gastos_caja_chica.filter(fecha__gte=fecha_inicio)
        vales_caja_chica = vales_caja_chica.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        gastos_caja_chica = gastos_caja_chica.filter(fecha__lte=fecha_fin)
        vales_caja_chica = vales_caja_chica.filter(fecha__lte=fecha_fin)

    # --- Saldo inicial dinámico en modo flujo por mes ---
    if modo == "flujo" and mes and anio and empresa:
        mes = int(mes)
        anio = int(anio)
        saldo_inicial = float(empresa.saldo_inicial or 0)
        # Determina el año de inicio (puedes ajustar si tienes fecha de inicio real)
        anio_inicio = empresa.fecha_creacion.year if hasattr(empresa, 'fecha_creacion') else anio
        for y in range(anio_inicio, anio + 1):
            mes_inicio = 1
            mes_fin = mes - 1 if y == anio else 12
            for m in range(mes_inicio, mes_fin + 1):
                fecha_inicio_loop = datetime.date(y, m, 1)
                if m == 12:
                    fecha_fin_loop = datetime.date(y, 12, 31)
                else:
                    fecha_fin_loop = datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
                pagos_loop = Pago.objects.exclude(forma_pago="nota_credito").filter(
                    factura__empresa_id=empresa_id,
                    fecha_pago__gte=fecha_inicio_loop,
                    fecha_pago__lte=fecha_fin_loop,
                )
                cobros_otros_loop = CobroOtrosIngresos.objects.filter(
                    factura__empresa_id=empresa_id,
                    fecha_cobro__gte=fecha_inicio_loop,
                    fecha_cobro__lte=fecha_fin_loop,
                )
                gastos_loop = PagoGasto.objects.filter(
                    gasto__empresa_id=empresa_id,
                    fecha_pago__gte=fecha_inicio_loop,
                    fecha_pago__lte=fecha_fin_loop,
                )
                total_ingresos_loop = float(
                    pagos_loop.aggregate(total=Sum("monto"))["total"] or 0
                ) + float(cobros_otros_loop.aggregate(total=Sum("monto"))["total"] or 0)
                total_gastos_loop = float(
                    gastos_loop.aggregate(total=Sum("monto"))["total"] or 0
                )
                saldo_inicial += total_ingresos_loop - total_gastos_loop
        # --- Fin de saldo inicial dinámico ---

    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
        gastos = gastos.filter(fecha__gte=fecha_inicio)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__gte=fecha_inicio)
        vales_caja_chica = vales_caja_chica.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)
        gastos = gastos.filter(fecha__lte=fecha_fin)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__lte=fecha_fin)
        vales_caja_chica = vales_caja_chica.filter(fecha__lte=fecha_fin)

    # PAGOS POR IDENTIFICAR
    pagos_por_identificar = Pago.objects.filter(
        factura__isnull=True,
        identificado=False
    )
    if empresa_id:
        pagos_por_identificar = pagos_por_identificar.filter(empresa_id=empresa_id)
    if fecha_inicio:
        pagos_por_identificar = pagos_por_identificar.filter(fecha_pago__gte=fecha_inicio)
    if fecha_fin:
        pagos_por_identificar = pagos_por_identificar.filter(fecha_pago__lte=fecha_fin)
    total_pagos_por_identificar = pagos_por_identificar.aggregate(total=Sum("monto"))["total"] or 0

    saldo_final_flujo = None
    total_gastos = 0.0
    gastos_por_grupo = []

    if modo == "flujo":
        pagos_modo = pagos
        cobros_otros_modo = cobros_otros
        gastos_modo = PagoGasto.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        )
        if empresa_id:
            gastos_modo = gastos_modo.filter(gasto__empresa_id=empresa_id)
        ingresos_qs = (
            pagos_modo.annotate(
                origen=Case(
                    When(factura__local__isnull=False, then=Value("Locales")),
                    When(
                        factura__area_comun__isnull=False, then=Value("Áreas Comunes")
                    ),
                    default=Value("Sin origen"),
                    output_field=CharField(),
                )
            )
            .values("origen")
            .annotate(total=Sum("monto"))
            .order_by("origen")
        )
        otros_ingresos_qs = (
            cobros_otros_modo.select_related("factura__tipo_ingreso")
            .values("factura__tipo_ingreso__nombre")
            .annotate(total=Sum("monto"))
            .order_by("factura__tipo_ingreso__nombre")
        )
        ingresos_por_origen = OrderedDict()
        for x in ingresos_qs:
            origen = (x["origen"] or "Sin origen").strip().title()
            ingresos_por_origen[origen] = float(x["total"])
        for x in otros_ingresos_qs:
            tipo = (
                (x["factura__tipo_ingreso__nombre"] or "Otros ingresos").strip().title()
            )
            ingresos_por_origen[f"Otros ingresos - {tipo}"] = float(x["total"])
        ingresos_por_origen["Depositos no identificados"] = float(total_pagos_por_identificar)    
        total_ingresos = float(sum(ingresos_por_origen.values()))

        # Agrupar y sumar todos los gastos por tipo real (gastos normales, caja chica y vales)
        gastos_por_tipo_dict = {}
        tipos_gasto = set()
        tipos_gasto.update(
            [
                g["gasto__tipo_gasto__nombre"]
                for g in gastos_modo.values("gasto__tipo_gasto__nombre")
                if g["gasto__tipo_gasto__nombre"]
            ]
        )
        # Agrupa y suma en una sola consulta para cada fuente
        gastos_modo_agrupados = gastos_modo.values(
            "gasto__tipo_gasto__nombre"
        ).annotate(suma=Sum("monto"))
        gastos_caja_agrupados = gastos_caja_chica.values("tipo_gasto__nombre").annotate(
            suma=Sum("importe")
        )
        gastos_vales_agrupados = vales_caja_chica.values("tipo_gasto__nombre").annotate(
            suma=Sum("importe")
        )

        # Unifica todos los tipos
        tipos_gasto = set()
        tipos_gasto.update(
            g["gasto__tipo_gasto__nombre"]
            for g in gastos_modo_agrupados
            if g["gasto__tipo_gasto__nombre"]
        )
        tipos_gasto.update(
            g["tipo_gasto__nombre"]
            for g in gastos_caja_agrupados
            if g["tipo_gasto__nombre"]
        )
        tipos_gasto.update(
            g["tipo_gasto__nombre"]
            for g in gastos_vales_agrupados
            if g["tipo_gasto__nombre"]
        )

        # Crea diccionarios para acceso rápido
        dict_modo = {
            g["gasto__tipo_gasto__nombre"]: g["suma"] for g in gastos_modo_agrupados
        }
        dict_caja = {g["tipo_gasto__nombre"]: g["suma"] for g in gastos_caja_agrupados}
        dict_vales = {
            g["tipo_gasto__nombre"]: g["suma"] for g in gastos_vales_agrupados
        }

        for tipo in tipos_gasto:
            nombre_tipo = (tipo or "Sin tipo").strip().title()
            total_gastos_modo = float(dict_modo.get(tipo, 0) or 0)
            total_gastos_caja = float(dict_caja.get(tipo, 0) or 0)
            total_vales = float(dict_vales.get(tipo, 0) or 0)
            total = total_gastos_modo + total_gastos_caja + total_vales
            if total > 0:
                gastos_por_tipo_dict[nombre_tipo] = total

        gastos_por_tipo = [
            {"tipo": tipo, "total": total}
            for tipo, total in gastos_por_tipo_dict.items()
        ]

        estructura_gastos = OrderedDict()
        # Gastos modo flujo
        for g in gastos_modo.values(
            "gasto__tipo_gasto__subgrupo__grupo__nombre",
            "gasto__tipo_gasto__subgrupo__nombre",
            "gasto__tipo_gasto__nombre",
        ).annotate(total=Sum("monto")):
            grupo = (
                (g["gasto__tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["gasto__tipo_gasto__subgrupo__nombre"] or "Sin subgrupo")
                .strip()
                .title()
            )
            tipo = (g["gasto__tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = {}
            estructura_gastos[grupo][subgrupo][tipo] = (
                estructura_gastos[grupo][subgrupo].get(tipo, 0) + total
            )

        # Caja chica modo flujo
        for g in gastos_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (
                (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            )
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = {}
            estructura_gastos[grupo][subgrupo][tipo] = (
                estructura_gastos[grupo][subgrupo].get(tipo, 0) + total
            )

        # Vales de caja chica modo flujo
        for g in vales_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (
                (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            )
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = {}
            estructura_gastos[grupo][subgrupo][tipo] = (
                estructura_gastos[grupo][subgrupo].get(tipo, 0) + total
            )

        # Convertir los dicts de tipos a listas para compatibilidad con el template
        for grupo in estructura_gastos:
            for subgrupo in estructura_gastos[grupo]:
                tipos_dict = estructura_gastos[grupo][subgrupo]
                estructura_gastos[grupo][subgrupo] = [
                    {"tipo": tipo, "total": total} for tipo, total in tipos_dict.items()
                ]
        #total_gastos = sum([g["total"] for g in gastos_por_tipo])
        total_gastos = sum(
            sum(tipo["total"] for tipo in tipos)
            for subgrupos in estructura_gastos.values()
            for tipos in subgrupos.values()
        )
        saldo_final_flujo = (
            float(saldo_inicial) + float(total_ingresos) - float(total_gastos)
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
        origenes = (
            facturas_cuotas.annotate(
                origen=Case(
                    When(local__isnull=False, then=Value("Locales")),
                    When(area_comun__isnull=False, then=Value("Áreas Comunes")),
                    default=Value("Sin origen"),
                    output_field=CharField(),
                )
            )
            .values("origen")
            .annotate(total=Sum("monto"))
            .order_by("origen")
        )
        for x in origenes:
            origen = (x["origen"] or "Sin origen").strip().title()
            ingresos_por_origen[origen] = float(x["total"])
        otros = (
            facturas_otros.values("tipo_ingreso__nombre")
            .annotate(total=Sum("monto"))
            .order_by("tipo_ingreso__nombre")
        )
        for x in otros:
            tipo = (x["tipo_ingreso__nombre"] or "Otros ingresos").strip().title()
            ingresos_por_origen[f"Otros ingresos - {tipo}"] = float(x["total"])
        ingresos_por_origen["Depositos no identificados"] = float(total_pagos_por_identificar)    
        total_ingresos = float(sum(ingresos_por_origen.values()))

        # Agrupar y sumar todos los gastos por tipo real (gastos normales, caja chica y vales)
        gastos_por_tipo_dict = {}
        tipos_gasto = set()
        tipos_gasto.update(
            [g["tipo_gasto__nombre"] for g in gastos.values("tipo_gasto__nombre")]
        )
        tipos_gasto.update(
            [
                g["tipo_gasto__nombre"]
                for g in gastos_caja_chica.values("tipo_gasto__nombre")
            ]
        )
        tipos_gasto.update(
            [
                g["tipo_gasto__nombre"]
                for g in vales_caja_chica.values("tipo_gasto__nombre")
            ]
        )
        for tipo in tipos_gasto:
            if tipo and tipo not in ["Gastos de caja chica", "Vales de caja chica"]:
                nombre_tipo = (tipo or "Sin tipo").strip().title()
                total = 0.0
                total_gastos = (
                    gastos.filter(tipo_gasto__nombre=tipo).aggregate(suma=Sum("monto"))[
                        "suma"
                    ]
                    or 0
                )
                total_gastos_caja = (
                    gastos_caja_chica.filter(tipo_gasto__nombre=tipo).aggregate(
                        suma=Sum("importe")
                    )["suma"]
                    or 0
                )
                total_vales = (
                    vales_caja_chica.filter(tipo_gasto__nombre=tipo).aggregate(
                        suma=Sum("importe")
                    )["suma"]
                    or 0
                )
                total = (
                    float(total_gastos) + float(total_gastos_caja) + float(total_vales)
                )
                if total > 0:
                    gastos_por_tipo_dict[nombre_tipo] = total

        gastos_por_tipo = []
        for tipo, total in gastos_por_tipo_dict.items():
            gastos_por_tipo.append({"tipo": tipo, "total": total})

        # Unificar gastos normales, caja chica y vales por grupo, subgrupo y tipo
        estructura_gastos = OrderedDict()
        # Gastos normales
        for g in gastos.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("monto")):
            grupo = (
                (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            )
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = {}
            estructura_gastos[grupo][subgrupo][tipo] = (
                estructura_gastos[grupo][subgrupo].get(tipo, 0) + total
            )

        # Caja chica
        for g in gastos_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (
                (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            )
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = {}
            estructura_gastos[grupo][subgrupo][tipo] = (
                estructura_gastos[grupo][subgrupo].get(tipo, 0) + total
            )

        # Vales de caja chica
        for g in vales_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (
                (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            )
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = {}
            estructura_gastos[grupo][subgrupo][tipo] = (
                estructura_gastos[grupo][subgrupo].get(tipo, 0) + total
            )

        # Convertir los dicts de tipos a listas para compatibilidad con el template
        for grupo in estructura_gastos:
            for subgrupo in estructura_gastos[grupo]:
                tipos_dict = estructura_gastos[grupo][subgrupo]
                estructura_gastos[grupo][subgrupo] = [
                    {"tipo": tipo, "total": total} for tipo, total in tipos_dict.items()
                ]
        total_gastos = sum([g["total"] for g in gastos_por_tipo])
        saldo_final_flujo = None

    saldo = float(total_ingresos) - float(total_gastos)

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
            "saldo_inicial": saldo_inicial,
            "saldo_final": saldo_final,
            "saldo_final_flujo": saldo_final_flujo,
            "meses_unicos": meses_unicos,
            "anios_unicos": anios_unicos,
            "mes_letra": mes_letra,
            "total_pagos_por_identificar": total_pagos_por_identificar,
        },
    )


@login_required
def exportar_estado_resultados_excel(request):
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    periodo = request.GET.get("periodo")
    modo = request.GET.get("modo", "flujo")
    hoy = datetime.date.today()

    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or ""

    empresa_nombre = ""
    if empresa_id:
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            empresa_nombre = empresa.nombre
            saldo_inicial = float(empresa.saldo_inicial or 0)
        except Empresa.DoesNotExist:
            saldo_inicial = 0
    else:
        saldo_inicial = 0

    pagos = Pago.objects.exclude(forma_pago="nota_credito")
    cobros_otros = CobroOtrosIngresos.objects.select_related(
        "factura", "factura__empresa"
    )
    gastos = Gasto.objects.all()
    gastos_caja_chica = GastoCajaChica.objects.all()
    vales_caja_chica = ValeCaja.objects.all()

    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = "periodo_actual"

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
        pass
    else:
        fecha_inicio = None
        fecha_fin = None

    if empresa_id:
        pagos = pagos.filter(factura__empresa_id=empresa_id)
        cobros_otros = cobros_otros.filter(factura__empresa_id=empresa_id)
        gastos = gastos.filter(empresa_id=empresa_id)
        gastos_caja_chica = gastos_caja_chica.filter(fondeo__empresa_id=empresa_id)
        vales_caja_chica = vales_caja_chica.filter(fondeo__empresa_id=empresa_id)
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            saldo_inicial = float(empresa.saldo_inicial or 0)
        except Empresa.DoesNotExist:
            saldo_inicial = 0
    else:
        saldo_inicial = 0

    # --- Saldo inicial dinámico en modo flujo por mes y año (recorre años si aplica) ---
    if modo == "flujo" and mes and anio and empresa_id:
        mes = int(mes)
        anio = int(anio)
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            saldo_inicial = float(empresa.saldo_inicial or 0)
            anio_inicio = empresa.fecha_creacion.year if hasattr(empresa, 'fecha_creacion') else anio
        except Empresa.DoesNotExist:
            saldo_inicial = 0
            anio_inicio = anio
        for y in range(anio_inicio, anio + 1):
            mes_inicio = 1
            mes_fin = mes - 1 if y == anio else 12
            for m in range(mes_inicio, mes_fin + 1):
                fecha_inicio_loop = datetime.date(y, m, 1)
                if m == 12:
                    fecha_fin_loop = datetime.date(y, 12, 31)
                else:
                    fecha_fin_loop = datetime.date(y, m + 1, 1) - datetime.timedelta(
                        days=1
                    )
                pagos_loop = Pago.objects.exclude(forma_pago="nota_credito").filter(
                    factura__empresa_id=empresa_id,
                    fecha_pago__gte=fecha_inicio_loop,
                    fecha_pago__lte=fecha_fin_loop,
                )
                cobros_otros_loop = CobroOtrosIngresos.objects.filter(
                    factura__empresa_id=empresa_id,
                    fecha_cobro__gte=fecha_inicio_loop,
                    fecha_cobro__lte=fecha_fin_loop,
                )
                gastos_loop = PagoGasto.objects.filter(
                    gasto__empresa_id=empresa_id,
                    fecha_pago__gte=fecha_inicio_loop,
                    fecha_pago__lte=fecha_fin_loop,
                )
                total_ingresos_loop = float(
                    pagos_loop.aggregate(total=Sum("monto"))["total"] or 0
                ) + float(cobros_otros_loop.aggregate(total=Sum("monto"))["total"] or 0)
                total_gastos_loop = float(
                    gastos_loop.aggregate(total=Sum("monto"))["total"] or 0
                )
                saldo_inicial += total_ingresos_loop - total_gastos_loop
    # --- Fin de saldo inicial dinámico ---

    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
        gastos = gastos.filter(fecha__gte=fecha_inicio)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__gte=fecha_inicio)
        vales_caja_chica = vales_caja_chica.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)
        gastos = gastos.filter(fecha__lte=fecha_fin)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__lte=fecha_fin)
        vales_caja_chica = vales_caja_chica.filter(fecha__lte=fecha_fin)

    # PAGOS POR IDENTIFICAR
    pagos_por_identificar = Pago.objects.filter(
        factura__isnull=True, identificado=False
    )
    if empresa_id:
        pagos_por_identificar = pagos_por_identificar.filter(empresa_id=empresa_id)
    if fecha_inicio:
        pagos_por_identificar = pagos_por_identificar.filter(
            fecha_pago__gte=fecha_inicio
        )
    if fecha_fin:
        pagos_por_identificar = pagos_por_identificar.filter(fecha_pago__lte=fecha_fin)
    total_pagos_por_identificar = (
        pagos_por_identificar.aggregate(total=Sum("monto"))["total"] or 0
    )

    saldo_final_flujo = None
    total_gastos = 0.0
    gastos_por_grupo = []

    if modo == "flujo":
        pagos_modo = pagos
        cobros_otros_modo = cobros_otros
        gastos_modo = PagoGasto.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        )
        if empresa_id:
            gastos_modo = gastos_modo.filter(gasto__empresa_id=empresa_id)
        ingresos_qs = (
            pagos_modo.annotate(
                origen=Case(
                    When(factura__local__isnull=False, then=Value("Locales")),
                    When(
                        factura__area_comun__isnull=False, then=Value("Áreas Comunes")
                    ),
                    default=Value("Sin origen"),
                    output_field=CharField(),
                )
            )
            .values("origen")
            .annotate(total=Sum("monto"))
            .order_by("origen")
        )
        otros_ingresos_qs = (
            cobros_otros_modo.values("factura__tipo_ingreso__nombre")
            .annotate(total=Sum("monto"))
            .order_by("factura__tipo_ingreso__nombre")
        )
        ingresos_por_origen = OrderedDict()
        for x in ingresos_qs:
            origen = (x["origen"] or "Sin origen").strip().title()
            ingresos_por_origen[origen] = float(x["total"])
        for x in otros_ingresos_qs:
            tipo = (
                (x["factura__tipo_ingreso__nombre"] or "Otros ingresos").strip().title()
            )
            ingresos_por_origen[f"Otros ingresos - {tipo}"] = float(x["total"])
        ingresos_por_origen["Depositos no identificados"] = float(
            total_pagos_por_identificar
        )
        total_ingresos = float(sum(ingresos_por_origen.values()))
        # Agrupar y sumar todos los gastos por tipo real (gastos normales, caja chica y vales)
        gastos_por_grupo = (
            gastos_modo.values(
                "gasto__tipo_gasto__subgrupo__grupo__nombre",
                "gasto__tipo_gasto__subgrupo__nombre",
                "gasto__tipo_gasto__nombre",
            )
            .annotate(total=Sum("monto"))
            .order_by(
                "gasto__tipo_gasto__subgrupo__grupo__nombre",
                "gasto__tipo_gasto__subgrupo__nombre",
                "gasto__tipo_gasto__nombre",
            )
        )
        estructura_gastos = OrderedDict()
        for g in gastos_por_grupo:
            grupo = (
                (g["gasto__tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["gasto__tipo_gasto__subgrupo__nombre"] or "Sin subgrupo")
                .strip()
                .title()
            )
            tipo = (g["gasto__tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        # --- AGREGA GASTOS DE CAJA CHICA Y VALES EN FLUJO ---
        for g in gastos_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo").strip().title()
            subgrupo = (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        for g in vales_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo").strip().title()
            subgrupo = (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        total_gastos = sum(
            sum(tipo["total"] for tipo in tipos)
            for subgrupos in estructura_gastos.values()
            for tipos in subgrupos.values()
        )
        saldo_final_flujo = (
            float(saldo_inicial) + float(total_ingresos) - float(total_gastos)
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
        origenes = (
            facturas_cuotas.annotate(
                origen=Case(
                    When(local__isnull=False, then=Value("Locales")),
                    When(area_comun__isnull=False, then=Value("Áreas Comunes")),
                    default=Value("Sin origen"),
                    output_field=CharField(),
                )
            )
            .values("origen")
            .annotate(total=Sum("monto"))
            .order_by("origen")
        )
        for x in origenes:
            origen = (x["origen"] or "Sin origen").strip().title()
            ingresos_por_origen[origen] = float(x["total"])
        otros = (
            facturas_otros.values("tipo_ingreso__nombre")
            .annotate(total=Sum("monto"))
            .order_by("tipo_ingreso__nombre")
        )
        for x in otros:
            tipo = (x["tipo_ingreso__nombre"] or "Otros ingresos").strip().title()
            ingresos_por_origen[f"Otros ingresos - {tipo}"] = float(x["total"])
        total_ingresos = float(sum(ingresos_por_origen.values()))
        gastos_por_grupo = (
            gastos.values(
                "tipo_gasto__subgrupo__grupo__nombre",
                "tipo_gasto__subgrupo__nombre",
                "tipo_gasto__nombre",
            )
            .annotate(total=Sum("monto"))
            .order_by(
                "tipo_gasto__subgrupo__grupo__nombre",
                "tipo_gasto__subgrupo__nombre",
                "tipo_gasto__nombre",
            )
        )
        estructura_gastos = OrderedDict()
        for g in gastos_por_grupo:
            grupo = (
                (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo")
                .strip()
                .title()
            )
            subgrupo = (
                (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            )
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        # --- AGREGA GASTOS DE CAJA CHICA Y VALES EN RESULTADOS ---
        for g in gastos_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo").strip().title()
            subgrupo = (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        for g in vales_caja_chica.values(
            "tipo_gasto__subgrupo__grupo__nombre",
            "tipo_gasto__subgrupo__nombre",
            "tipo_gasto__nombre",
        ).annotate(total=Sum("importe")):
            grupo = (g["tipo_gasto__subgrupo__grupo__nombre"] or "Sin grupo").strip().title()
            subgrupo = (g["tipo_gasto__subgrupo__nombre"] or "Sin subgrupo").strip().title()
            tipo = (g["tipo_gasto__nombre"] or "Sin tipo").strip().title()
            total = float(g["total"])
            if grupo not in estructura_gastos:
                estructura_gastos[grupo] = OrderedDict()
            if subgrupo not in estructura_gastos[grupo]:
                estructura_gastos[grupo][subgrupo] = []
            estructura_gastos[grupo][subgrupo].append({"tipo": tipo, "total": total})
        total_gastos = sum(
            sum(tipo["total"] for tipo in tipos)
            for subgrupos in estructura_gastos.values()
            for tipos in subgrupos.values()
        )
        saldo_final_flujo = None

    saldo = float(total_ingresos) - float(total_gastos)

    # --- Estilos ---
    bold = Font(bold=True)
    title_font = Font(size=14, bold=True)
    header_fill = PatternFill("solid", fgColor="BDD7EE")
    group_fill = PatternFill("solid", fgColor="DDEBF7")
    sub_fill = PatternFill("solid", fgColor="F7F7F7")
    border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000'),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Estado de Resultados"

    # --- Cabecera ---
    ws.merge_cells("A1:B1")
    ws["A1"] = "Estado de Resultados"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A2:B2")
    ws["A2"] = f"Empresa: {empresa_nombre}"
    ws["A2"].font = bold
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A3:B3")
    periodo_str = f"Periodo: {fecha_inicio} a {fecha_fin}"
    ws["A3"] = periodo_str
    ws["A3"].font = bold
    ws["A3"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A4:B4")
    ws["A4"] = f"Tipo: {'Flujo' if modo == 'flujo' else 'Resultados'}"
    ws["A4"].font = bold
    ws["A4"].alignment = Alignment(horizontal="center")
    ws.append([])

    row = ws.max_row + 1
    if modo == "flujo":
        ws.append(["Saldo inicial bancos", saldo_inicial])
        ws[f"A{row}"].font = bold
        ws[f"B{row}"].font = bold

    # --- Ingresos ---
    ws.append(["Ingresos", "Importe"])
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = header_fill
        cell.border = border
    for origen, monto in ingresos_por_origen.items():
        ws.append([origen, monto])
        ws[f"A{ws.max_row}"].fill = group_fill
        ws[f"A{ws.max_row}"].border = border
        ws[f"B{ws.max_row}"].border = border
    ws.append(["Total Ingresos", total_ingresos])
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = header_fill
        cell.border = border
    ws.append([])

    # --- Gastos ---
    ws.append(["Gastos", "Importe"])
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = header_fill
        cell.border = border
    for grupo, subgrupos in estructura_gastos.items():
        ws.append([grupo, ""])
        ws[f"A{ws.max_row}"].fill = group_fill
        ws[f"A{ws.max_row}"].font = bold
        ws[f"A{ws.max_row}"].border = border
        ws[f"B{ws.max_row}"].border = border
        for subgrupo, tipos in subgrupos.items():
            ws.append(["  " + subgrupo, ""])
            ws[f"A{ws.max_row}"].fill = sub_fill
            ws[f"A{ws.max_row}"].font = bold
            ws[f"A{ws.max_row}"].border = border
            ws[f"B{ws.max_row}"].border = border
            for tipo in tipos:
                ws.append(["    " + tipo["tipo"], tipo["total"]])
                ws[f"A{ws.max_row}"].border = border
                ws[f"B{ws.max_row}"].border = border
    ws.append(["Total Gastos", total_gastos])
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = header_fill
        cell.border = border
    ws.append([])

    # --- Resultado ---
    ws.append(["Resultado", saldo])
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = header_fill
        cell.border = border
    if modo == "flujo":
        ws.append(["Saldo final bancos", saldo_final_flujo])
        for cell in ws[ws.max_row]:
            cell.font = bold
            cell.fill = header_fill
            cell.border = border

    # --- Ajusta ancho de columnas ---
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 18

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=estado_resultados.xlsx"
    wb.save(response)
    return response


# reporte detalle saldos
@login_required
def cartera_vencida_por_origen(request):
    empresa_id = request.GET.get("empresa")
    hoy = timezone.now().date()
    filtro_origen = request.GET.get("filtro_origen", "")
    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or ""

    # Facturas de locales y áreas comunes
    facturas = Factura.objects.filter(
        estatus="pendiente",
        fecha_vencimiento__lt=hoy,
        monto__gt=0
    ).select_related('local', 'area_comun', 'cliente')

    if empresa_id:
        facturas = facturas.filter(empresa_id=empresa_id)

    # Agrupación y anotación en BD
    facturas_qs = facturas.annotate(
        origen_id=Case(
            When(local__isnull=False, then=F("local__id")),
            When(area_comun__isnull=False, then=F("area_comun__id")),
            default=Value(0),
            output_field=IntegerField(),
        ),
        origen_tipo=Case(
            When(local__isnull=False, then=Value("local")),
            When(area_comun__isnull=False, then=Value("area")),
            default=Value("sin_origen"),
            output_field=CharField(),
        ),
        origen_nombre=Case(
            When(local__isnull=False, then=F("local__numero")),
            When(area_comun__isnull=False, then=F("area_comun__numero")),
            default=Value("Sin origen"),
            output_field=CharField(),
        ),
        # saldo_calc=Case(
        #     When(saldo__isnull=False, then=F('saldo')),
        #     default=F('saldo_pendiente'),
        #     output_field=F('monto').__class__
        # )
    ).order_by("origen_tipo", "origen_nombre", "fecha_vencimiento")

    # Facturas otros ingresos
    facturas_oi = FacturaOtrosIngresos.objects.filter(
        estatus="pendiente",
        fecha_vencimiento__lt=hoy,
        monto__gt=0
    ).select_related('tipo_ingreso', 'cliente')

    if empresa_id:
        facturas_oi = facturas_oi.filter(empresa_id=empresa_id)

    facturas_oi_qs = facturas_oi.annotate(
        origen_id=F("tipo_ingreso__id"),
        origen_tipo=Value("tipoingreso", output_field=CharField()),
        origen_nombre=F("tipo_ingreso__nombre"),
        # saldo_calc=Case(
        #     When(saldo__isnull=False, then=F('saldo')),
        #     default=F('monto'),
        #     output_field=F('monto').__class__
        # )
    ).order_by("origen_nombre", "fecha_vencimiento")

    # Construcción del resultado
    origenes_dict = {}

    for f in facturas_qs:
        if f.origen_tipo == "local":
            origen_id = f"local_{f.origen_id}"
            origen_nombre = f"Local: {f.origen_nombre}"
        elif f.origen_tipo == "area":
            origen_id = f"area_{f.origen_id}"
            origen_nombre = f"Área Común: {f.origen_nombre}"
        else:
            origen_id = "sin_origen"
            origen_nombre = "Sin origen"

        if origen_id not in origenes_dict:
            origenes_dict[origen_id] = {
                "origen_nombre": origen_nombre,
                "total_vencido": 0,
                "facturas": []
            }
        saldo = float(f.saldo_pendiente or 0)
        origenes_dict[origen_id]["facturas"].append(
            {
                "cliente": f.cliente.nombre if f.cliente else "Desconocido",
                "factura_id": f.id,
                "folio": f.folio,
                "fecha_vencimiento": f.fecha_vencimiento,
                "dias_vencidos": (hoy - f.fecha_vencimiento).days,
                "monto": float(f.monto),
                "saldo": saldo,
                "concepto": f.observaciones,
            }
        )
        origenes_dict[origen_id]["total_vencido"] += saldo

    for f in facturas_oi_qs:
        origen_id = f"tipoingreso_{f.origen_id}"
        origen_nombre = f"Tipo de Ingreso: {f.origen_nombre}"
        if origen_id not in origenes_dict:
            origenes_dict[origen_id] = {
                "origen_nombre": origen_nombre,
                "total_vencido": 0,
                "facturas": []
            }
        saldo = float(f.saldo or 0)
        origenes_dict[origen_id]["facturas"].append(
            {
                "cliente": f.cliente.nombre if f.cliente else "Desconocido",
                "factura_id": f.id,
                "folio": f.folio,
                "fecha_vencimiento": f.fecha_vencimiento,
                "dias_vencidos": (hoy - f.fecha_vencimiento).days,
                "monto": float(f.monto),
                "saldo": saldo,
                "concepto": f.observaciones,
            }
        )
        origenes_dict[origen_id]["total_vencido"] += saldo

    if filtro_origen in ("local", "area", "tipoingreso"):
        resultado = [
            origen
            for key, origen in origenes_dict.items()
            if key.startswith(filtro_origen + "_")
        ]
    else:
        resultado = list(origenes_dict.values())

    # resultado = list(origenes_dict.values())
    total_cartera = sum(origen["total_vencido"] for origen in resultado)
    return render(
        request,
        "informes_financieros/cartera_vencida_x_origen.html",
        {
            "cartera_vencida": resultado,
            "total_cartera": total_cartera,
            "request": request,
        },
    )


@login_required
def exportar_cartera_vencida_excel(request):
    empresa_id = request.GET.get("empresa")
    hoy = timezone.now().date()
    filtro_origen = request.GET.get("filtro_origen", "")

    if not request.user.is_superuser:
        empresa_id = str(request.user.perfilusuario.empresa.id)
    else:
        empresa_id = request.GET.get("empresa") or ""

    facturas = Factura.objects.filter(
        estatus="pendiente", fecha_vencimiento__lt=hoy, monto__gt=0
    ).select_related("local", "area_comun", "cliente")
    facturas_oi = FacturaOtrosIngresos.objects.filter(
        estatus="pendiente", fecha_vencimiento__lt=hoy, monto__gt=0
    ).select_related("tipo_ingreso", "cliente")

    if empresa_id:
        facturas = facturas.filter(empresa_id=empresa_id)
        facturas_oi = facturas_oi.filter(empresa_id=empresa_id)

    # Agrupa igual que la vista HTML
    origenes_dict = {}
    for factura in facturas.order_by(
        "local__numero", "area_comun__numero", "fecha_vencimiento"
    ):
        if factura.local:
            origen_id = f"local_{factura.local.id}"
            origen_nombre = f"Local: {factura.local.numero}"
        elif factura.area_comun:
            origen_id = f"area_{factura.area_comun.id}"
            origen_nombre = f"Área Común: {factura.area_comun.numero}"
        else:
            origen_id = "sin_origen"
            origen_nombre = "Sin origen"

        if origen_id not in origenes_dict:
            origenes_dict[origen_id] = {
                "origen_nombre": origen_nombre,
                "total_vencido": 0,
                "facturas": []
            }
        saldo = float(getattr(factura, "saldo", factura.saldo_pendiente))
        origenes_dict[origen_id]["facturas"].append(
            {
                "cliente": factura.cliente.nombre if factura.cliente else "Desconocido",
                "folio": factura.folio,
                "fecha_vencimiento": factura.fecha_vencimiento,
                "dias_vencidos": (hoy - factura.fecha_vencimiento).days,
                "monto": float(factura.monto),
                "saldo": saldo,
                "concepto": factura.observaciones,
            }
        )
        origenes_dict[origen_id]["total_vencido"] += saldo

    for factura in facturas_oi.order_by("tipo_ingreso__nombre", "fecha_vencimiento"):
        origen_id = f"tipoingreso_{factura.tipo_ingreso.id}"
        origen_nombre = f"Tipo de Ingreso: {factura.tipo_ingreso.nombre}"

        if origen_id not in origenes_dict:
            origenes_dict[origen_id] = {
                "origen_nombre": origen_nombre,
                "total_vencido": 0,
                "facturas": []
            }
        saldo = float(getattr(factura, "saldo", factura.saldo))
        origenes_dict[origen_id]["facturas"].append(
            {
                "cliente": factura.cliente.nombre if factura.cliente else "Desconocido",
                "folio": factura.folio,
                "fecha_vencimiento": factura.fecha_vencimiento,
                "dias_vencidos": (hoy - factura.fecha_vencimiento).days,
                "monto": float(factura.monto),
                "saldo": saldo,
                "concepto": factura.observaciones,
            }
        )
        origenes_dict[origen_id]["total_vencido"] += saldo

    # Aplica el filtro igual que en la vista HTML
    if filtro_origen in ("local", "area", "tipoingreso"):
        resultado = [
            origen
            for key, origen in origenes_dict.items()
            if key.startswith(filtro_origen + "_")
        ]
    else:
        resultado = list(origenes_dict.values())

    # resultado = list(origenes_dict.values())
    total_cartera = sum(origen["total_vencido"] for origen in resultado)

    # --- Excel ---
    wb = Workbook()
    ws = wb.active
    ws.title = "Cartera Vencida"

    bold = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="BDD7EE")
    border = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )

    ws.append(["Cartera Vencida por Origen"])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws["A1"].font = Font(size=14, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center")

    row = 2
    for origen in resultado:
        ws.append(
            [origen["origen_nombre"], f"Total vencido: ${origen['total_vencido']:.2f}"]
        )
        ws[f"A{row}"].font = bold
        ws[f"A{row}"].fill = header_fill
        ws[f"A{row}"].border = border
        ws[f"B{row}"].font = bold
        ws[f"B{row}"].fill = header_fill
        ws[f"B{row}"].border = border
        row += 1
        ws.append(
            [
                "Cliente",
                "Folio",
                "Fecha Vencimiento",
                "Días Vencidos",
                "Monto",
                "Saldo",
                "Concepto",
            ]
        )
        for col in "ABCDEFG"[:7]:
            ws[f"{col}{row}"].font = bold
            ws[f"{col}{row}"].fill = header_fill
            ws[f"{col}{row}"].border = border
        row += 1
        for factura in origen["facturas"]:
            ws.append(
                [
                    factura["cliente"],
                    factura["folio"],
                    factura["fecha_vencimiento"].strftime("%Y-%m-%d"),
                    factura["dias_vencidos"],
                    factura["monto"],
                    factura["saldo"],
                    factura["concepto"] or "",
                ]
            )
            for col in "ABCDEFG"[:7]:
                ws[f"{col}{row}"].border = border
            row += 1
        ws.append([])
        row += 1

    ws.append(["Gran Total Vencido", total_cartera])
    ws[f"A{row}"].font = bold
    ws[f"B{row}"].font = bold
    ws[f"A{row}"].fill = header_fill
    ws[f"B{row}"].fill = header_fill
    ws[f"A{row}"].border = border
    ws[f"B{row}"].border = border

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 30

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=cartera_vencida.xlsx"
    wb.save(response)
    return response
