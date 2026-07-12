from decimal import Decimal, InvalidOperation
import json
import io
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
#from httpcore import request
from facturacion.models import CobroOtrosIngresos, Pago
from gastos.models import PagoGasto
from .forms import EstadoCuentaBancarioForm, ConciliacionBancariaForm
from .models import ConciliacionBancaria, EstadoCuentaBancario, MovimientoEstadoCuenta
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from django.db import transaction
from calendar import monthrange
from .utils import calcular_saldo_cuenta_periodo, get_o_crear_periodo
from .models import SaldoCuentaPeriodo
from empresas.models import CuentaBancaria, Empresa
import datetime
from django.utils import timezone


################################# VISTAS PARA CARGAR ESTADOS DE CUENTA Y CONCILIAR ########################################
@login_required
def cargar_estado_cuenta(request):
    empresa = request.user.perfilusuario.empresa

    if request.method == "POST":
        form = EstadoCuentaBancarioForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            estado = form.save(commit=False)
            estado.usuario = request.user
            estado.empresa = empresa
            estado.nombre_original = request.FILES["archivo"].name
            estado.save()

            ok, mensaje = procesar_movimientos_estado_cuenta(
                estado, request.FILES["archivo"]
            )

            if not ok:
                estado.archivo.delete(save=False)
                estado.delete()
                return render(
                    request,
                    "conciliacion/cargar_estado.html",
                    {
                        "form": form,
                        "error": mensaje,
                    },
                )

            return redirect("conciliaciones:conciliar", estado_id=estado.id)
    else:
        form = EstadoCuentaBancarioForm(empresa=empresa)

    return render(request, "conciliacion/cargar_estado.html", {"form": form})


def _buscar_columna(columnas, aliases):
    for columna in columnas:
        nombre = str(columna).strip().lower()
        if any(alias in nombre for alias in aliases):
            return columna
    return None


def _normalizar_monto(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, Decimal):
        monto = valor
    elif isinstance(valor, (int, float)):
        monto = Decimal(str(valor))
    else:
        texto = str(valor).strip()
        if not texto:
            return None

        texto = texto.replace("$", "")
        texto = texto.replace(",", "")
        texto = texto.replace(" ", "")
        texto = texto.replace("(", "-")
        texto = texto.replace(")", "")

        try:
            monto = Decimal(texto)
        except InvalidOperation:
            return None

    return monto.quantize(Decimal("0.01"))


def _leer_dataframe_subido(archivo):
    nombre = archivo.name.lower()
    archivo.seek(0)

    if nombre.endswith(".csv"):
        contenido = archivo.read()

        texto = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                texto = contenido.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if texto is None:
            raise ValueError("No se pudo decodificar el archivo CSV.")

        return pd.read_csv(io.StringIO(texto), sep=None, engine="python")

    if nombre.endswith(".xls") or nombre.endswith(".xlsx"):
        archivo.seek(0)
        return pd.read_excel(archivo)

    raise ValueError("Formato no soportado. Sube un archivo CSV o Excel.")


def procesar_movimientos_estado_cuenta(estado, archivo):
    nombre = archivo.name.lower()

    if nombre.endswith(".pdf"):
        return False, "El formato PDF aun no esta soportado. Sube CSV o Excel."

    try:
        archivo.seek(0)

        if nombre.endswith(".csv"):
            df = _leer_dataframe_subido(archivo)
        elif nombre.endswith(".xls") or nombre.endswith(".xlsx"):
            df = _leer_dataframe_subido(archivo)
        else:
            return False, "Formato no soportado. Sube un archivo CSV o Excel."
    except (EmptyDataError, ParserError, ValueError):
        return False, "No se pudo leer el archivo o esta vacio."

    if df.empty:
        return False, "El archivo no contiene filas para importar."

    df.columns = [str(col).strip() for col in df.columns]

    col_fecha = _buscar_columna(df.columns, ["fecha"])
    col_desc = _buscar_columna(
        df.columns,
        [
            "descripcion",
            "descripción",
            "description",
            "concepto",
            "detalle",
            "movimiento",
        ],
    )
    col_monto = _buscar_columna(df.columns, ["monto", "importe", "cantidad"])
    col_cargo = _buscar_columna(df.columns, ["cargo", "retiro", "debito", "débito"])
    col_abono = _buscar_columna(
        df.columns, ["abono", "deposito", "depósito", "credito", "crédito"]
    )

    if not col_fecha:
        return False, "No se detecto la columna fecha."
    if not col_desc:
        return False, "No se detecto la columna descripcion."
    if not (col_monto or col_cargo or col_abono):
        return False, "No se detectaron columnas de monto, cargo o abono."

    MovimientoEstadoCuenta.objects.filter(estado_cuenta=estado).delete()

    creados = 0

    for _, row in df.iterrows():
        fecha = pd.to_datetime(row[col_fecha], errors="coerce", dayfirst=True)
        if pd.isna(fecha):
            continue

        valor_desc = row[col_desc]
        descripcion = "" if pd.isna(valor_desc) else str(valor_desc).strip()
        if not descripcion:
            descripcion = "Sin descripcion"

        if col_cargo or col_abono:
            monto_cargo = _normalizar_monto(row[col_cargo]) if col_cargo else None
            monto_abono = _normalizar_monto(row[col_abono]) if col_abono else None

            if monto_cargo is not None and monto_cargo != 0:
                MovimientoEstadoCuenta.objects.create(
                    estado_cuenta=estado,
                    fecha=fecha.date(),
                    descripcion=descripcion,
                    monto=abs(monto_cargo),
                    tipo="cargo",
                )
                creados += 1

            if monto_abono is not None and monto_abono != 0:
                MovimientoEstadoCuenta.objects.create(
                    estado_cuenta=estado,
                    fecha=fecha.date(),
                    descripcion=descripcion,
                    monto=abs(monto_abono),
                    tipo="abono",
                )
                creados += 1
        else:
            monto = _normalizar_monto(row[col_monto])
            if monto is None or monto == 0:
                continue

            tipo = "abono" if monto > 0 else "cargo"

            MovimientoEstadoCuenta.objects.create(
                estado_cuenta=estado,
                fecha=fecha.date(),
                descripcion=descripcion,
                monto=abs(monto),
                tipo=tipo,
            )
            creados += 1

    if creados == 0:
        return False, "No se importo ningun movimiento. Revisa encabezados y formato."

    return True, f"Se importaron {creados} movimientos."


def _key_movimiento(tipo, monto, fecha):
    monto_decimal = Decimal(str(monto)).quantize(Decimal("0.01"))
    return (tipo, monto_decimal, fecha)


def _decimal_2(valor):
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def _valor_sistema(movimiento, campo, default=None):
    if isinstance(movimiento, dict):
        return movimiento.get(campo, default)
    return getattr(movimiento, campo, default)


def _serializar_movimiento_banco(movimiento):
    return {
        "id": movimiento.id,
        "fecha": movimiento.fecha.isoformat(),
        "descripcion": movimiento.descripcion,
        "monto": float(_decimal_2(movimiento.monto)),
        "tipo": movimiento.tipo,
    }


def _serializar_movimiento_sistema(movimiento):
    fecha = _valor_sistema(movimiento, "fecha")
    monto = _valor_sistema(movimiento, "monto", 0)

    return {
        "id": _valor_sistema(movimiento, "id"),
        "fecha": fecha.isoformat() if fecha else "",
        "descripcion": _valor_sistema(movimiento, "descripcion", ""),
        "monto": float(_decimal_2(monto)),
        "tipo": _valor_sistema(movimiento, "tipo", ""),
        "origen": _valor_sistema(movimiento, "origen", ""),
    }


def _marcar_sistema_conciliado(movimiento_sistema, movimiento_banco):
    if isinstance(movimiento_sistema, dict):
        return

    update_fields = []

    if hasattr(movimiento_sistema, "conciliado"):
        movimiento_sistema.conciliado = True
        update_fields.append("conciliado")

    if hasattr(movimiento_sistema, "movimiento_estado_cuenta"):
        movimiento_sistema.movimiento_estado_cuenta = movimiento_banco
        update_fields.append("movimiento_estado_cuenta")

    if update_fields:
        movimiento_sistema.save(update_fields=update_fields)


def _limpiar_sistema_conciliado(movimiento_sistema):
    if isinstance(movimiento_sistema, dict):
        return

    update_fields = []

    if hasattr(movimiento_sistema, "conciliado"):
        movimiento_sistema.conciliado = False
        update_fields.append("conciliado")

    if hasattr(movimiento_sistema, "movimiento_estado_cuenta"):
        movimiento_sistema.movimiento_estado_cuenta = None
        update_fields.append("movimiento_estado_cuenta")

    if update_fields:
        movimiento_sistema.save(update_fields=update_fields)


def _buscar_mejor_candidato(
    movimiento_banco,
    movimientos_sistema_pendientes,
    fecha_inicio_periodo=None,
    fecha_fin_periodo=None,
    tolerancia_monto=Decimal("1.00"),
):
    monto_banco = _decimal_2(movimiento_banco.monto)
    fecha_banco = movimiento_banco.fecha
    tipo_banco = movimiento_banco.tipo

    mejor = None

    for idx, movimiento_sistema in enumerate(movimientos_sistema_pendientes):
        tipo_sistema = _valor_sistema(movimiento_sistema, "tipo")
        fecha_sistema = _valor_sistema(movimiento_sistema, "fecha")
        monto_sistema = _valor_sistema(movimiento_sistema, "monto")

        if tipo_sistema != tipo_banco or not fecha_sistema or monto_sistema is None:
            continue

        if fecha_inicio_periodo and fecha_fin_periodo:
            if not (fecha_inicio_periodo <= fecha_sistema <= fecha_fin_periodo):
                continue

        monto_sistema = _decimal_2(monto_sistema)
        diferencia_monto = abs(monto_banco - monto_sistema)
        diferencia_dias = abs((fecha_banco - fecha_sistema).days)

        monto_exacto = diferencia_monto == Decimal("0.00")
        monto_aproximado = diferencia_monto <= tolerancia_monto
        fecha_exacta = diferencia_dias == 0
        fecha_en_periodo = True

        if not (monto_exacto or monto_aproximado):
            continue

        if monto_exacto and fecha_exacta:
            prioridad = 0
            regla = "monto exacto y fecha exacta"
        elif monto_exacto and fecha_en_periodo:
            prioridad = 1
            regla = "monto exacto y fecha dentro del periodo"
        elif monto_aproximado and fecha_exacta:
            prioridad = 2
            regla = "monto aproximado y fecha exacta"
        else:
            prioridad = 3
            regla = "monto aproximado y fecha dentro del periodo"

        ranking = (prioridad, diferencia_monto, diferencia_dias, idx)

        if mejor is None or ranking < mejor["ranking"]:
            mejor = {
                "idx": idx,
                "movimiento": movimiento_sistema,
                "diferencia_monto": diferencia_monto,
                "diferencia_dias": diferencia_dias,
                "regla": regla,
                "ranking": ranking,
            }

    return mejor


def _rango_periodo_conciliacion(estado):
    fecha_base_inicio = estado.fecha_inicio or estado.fecha_fin
    fecha_base_fin = estado.fecha_fin or estado.fecha_inicio

    if not fecha_base_inicio or not fecha_base_fin:
        return None, None

    if fecha_base_inicio > fecha_base_fin:
        fecha_base_inicio, fecha_base_fin = fecha_base_fin, fecha_base_inicio

    inicio = fecha_base_inicio.replace(day=1)
    ultimo_dia_fin = monthrange(fecha_base_fin.year, fecha_base_fin.month)[1]
    fin = fecha_base_fin.replace(day=ultimo_dia_fin)

    return inicio, fin


def _movimientos_sistema_desde_modelos(estado):
    movimientos = []
    inicio_periodo, fin_periodo = _rango_periodo_conciliacion(estado)

    pagos = (
        Pago.objects.filter(
            empresa=estado.empresa,
            cuenta_bancaria=estado.cuenta_bancaria,
            fecha_pago__isnull=False,
        )
        .select_related("factura")
        .order_by("fecha_pago", "id")
    )

    if inicio_periodo and fin_periodo:
        pagos = pagos.filter(fecha_pago__range=(inicio_periodo, fin_periodo))

    for pago in pagos:
        descripcion = getattr(pago, "observaciones", "") or (
            f"Pago factura {pago.factura.folio}"
            if getattr(pago, "factura", None)
            else "Pago"
        )
        movimientos.append(
            {
                "id": f"pago-{pago.id}",
                "fecha": pago.fecha_pago,
                "descripcion": descripcion,
                "monto": pago.monto,
                "tipo": "abono",
                "origen": "Pago",
            }
        )

    cobros = (
        CobroOtrosIngresos.objects.filter(
            factura__empresa=estado.empresa,
            cuenta_bancaria=estado.cuenta_bancaria,
            fecha_cobro__isnull=False,
        )
        .select_related("factura")
        .order_by("fecha_cobro", "id")
    )

    if inicio_periodo and fin_periodo:
        cobros = cobros.filter(fecha_cobro__range=(inicio_periodo, fin_periodo))

    for cobro in cobros:
        descripcion = getattr(cobro, "observaciones", "") or (
            f"Cobro otros ingresos {cobro.factura.folio}"
            if getattr(cobro, "factura", None)
            else "Cobro otros ingresos"
        )
        movimientos.append(
            {
                "id": f"cobro-{cobro.id}",
                "fecha": cobro.fecha_cobro,
                "descripcion": descripcion,
                "monto": cobro.monto,
                "tipo": "abono",
                "origen": "CobroOtrosIngresos",
            }
        )

    pagos_gasto = (
        PagoGasto.objects.filter(
            gasto__empresa=estado.empresa,
            cuenta_bancaria=estado.cuenta_bancaria,
            fecha_pago__isnull=False,
        )
        .select_related("gasto")
        .order_by("fecha_pago", "id")
    )

    if inicio_periodo and fin_periodo:
        pagos_gasto = pagos_gasto.filter(
            fecha_pago__range=(inicio_periodo, fin_periodo)
        )

    for pago_gasto in pagos_gasto:
        descripcion = (
            getattr(pago_gasto, "referencia", "")
            or getattr(getattr(pago_gasto, "gasto", None), "descripcion", "")
            or "Pago gasto"
        )
        movimientos.append(
            {
                "id": f"gasto-{pago_gasto.id}",
                "fecha": pago_gasto.fecha_pago,
                "descripcion": descripcion,
                "monto": pago_gasto.monto,
                "tipo": "cargo",
                "origen": "PagoGasto",
            }
        )

    return movimientos


@transaction.atomic
def conciliar_estado_con_sistema(
    estado,
    tolerancia_monto=Decimal("1.00"),
):
    movimientos_banco = list(
        MovimientoEstadoCuenta.objects.filter(estado_cuenta=estado).order_by(
            "fecha", "id"
        )
    )
    movimientos_sistema_pendientes = list(_movimientos_sistema_desde_modelos(estado))
    inicio_periodo, fin_periodo = _rango_periodo_conciliacion(estado)

    conciliadas = []
    no_conciliadas_banco = []

    for movimiento_banco in movimientos_banco:
        mejor = _buscar_mejor_candidato(
            movimiento_banco,
            movimientos_sistema_pendientes,
            fecha_inicio_periodo=inicio_periodo,
            fecha_fin_periodo=fin_periodo,
            tolerancia_monto=tolerancia_monto,
        )

        if mejor:
            movimiento_sistema = mejor["movimiento"]
            movimientos_sistema_pendientes.pop(mejor["idx"])

            movimiento_banco.conciliado = True
            movimiento_banco.save(update_fields=["conciliado"])

            conciliadas.append(
                {
                    "banco": _serializar_movimiento_banco(movimiento_banco),
                    "sistema": _serializar_movimiento_sistema(movimiento_sistema),
                    "regla_coincidencia": mejor["regla"],
                    "diferencia_monto": float(mejor["diferencia_monto"]),
                    "diferencia_dias": mejor["diferencia_dias"],
                }
            )
        else:
            movimiento_banco.conciliado = False
            movimiento_banco.save(update_fields=["conciliado"])
            no_conciliadas_banco.append(_serializar_movimiento_banco(movimiento_banco))

    no_conciliadas_sistema = []
    for movimiento_sistema in movimientos_sistema_pendientes:
        no_conciliadas_sistema.append(
            _serializar_movimiento_sistema(movimiento_sistema)
        )

    return {
        "totales": {
            "conciliadas": len(conciliadas),
            "no_conciliadas_banco": len(no_conciliadas_banco),
            "no_conciliadas_sistema": len(no_conciliadas_sistema),
        },
        "conciliadas": conciliadas,
        "no_conciliadas_banco": no_conciliadas_banco,
        "no_conciliadas_sistema": no_conciliadas_sistema,
    }


@login_required
def conciliar_estado_cuenta(request, estado_id):
    estado = EstadoCuentaBancario.objects.get(id=estado_id)
    if request.method == "POST":
        form = ConciliacionBancariaForm(request.POST)
        if form.is_valid():
            resultado = conciliar_estado_con_sistema(estado)
            # Guarda o actualiza conciliación para ese estado de cuenta
            ConciliacionBancaria.objects.update_or_create(
                estado_cuenta=estado,
                defaults={
                    "empresa": estado.empresa,
                    "usuario": request.user,
                    "resumen": resultado,
                },
            )
            return redirect("conciliaciones:resultado", estado_id=estado.id)
    else:
        form = ConciliacionBancariaForm(initial={"estado_cuenta": estado})
    return render(
        request, "conciliacion/conciliar.html", {"form": form, "estado": estado}
    )


@login_required
def resultado_conciliacion(request, estado_id):
    estado = get_object_or_404(EstadoCuentaBancario, id=estado_id)
    conciliacion = (
        ConciliacionBancaria.objects.filter(estado_cuenta=estado)
        .order_by("-fecha_conciliacion")
        .first()
    )

    if not conciliacion:
        mensaje = "No se ha realizado la conciliación para este estado de cuenta."
        return render(
            request,
            "conciliacion/resultado.html",
            {"estado": estado, "mensaje": mensaje},
        )

    resumen = conciliacion.resumen

    # Si se guardó como string JSON, convertir a dict
    if isinstance(resumen, str):
        try:
            resumen = json.loads(resumen)
        except Exception:
            resumen = {}

    # Normaliza estructura para que el template siempre tenga llaves válidas
    if not isinstance(resumen, dict):
        resumen = {}

    resumen.setdefault("conciliadas", [])
    resumen.setdefault("no_conciliadas_banco", [])
    resumen.setdefault("no_conciliadas_sistema", [])
    resumen.setdefault("totales", {})
    resumen["totales"].setdefault("conciliadas", len(resumen["conciliadas"]))
    resumen["totales"].setdefault(
        "no_conciliadas_banco", len(resumen["no_conciliadas_banco"])
    )
    resumen["totales"].setdefault(
        "no_conciliadas_sistema", len(resumen["no_conciliadas_sistema"])
    )

    return render(
        request,
        "conciliacion/resultado.html",
        {
            "estado": estado,
            "conciliacion": conciliacion,
            "resumen": resumen,
        },
    )


#################################  VISTAS PARA SALDOS DE CUENTA POR PERIODO  ########################################
@login_required
def saldos_periodo(request):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    hoy = datetime.date.today()
    anio = int(request.GET.get("anio", hoy.year))
    mes = int(request.GET.get("mes", hoy.month))

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)

    periodos = []
    for cuenta in cuentas:
        periodo, movimientos = get_o_crear_periodo(cuenta, empresa, anio, mes)
        saldo_final = periodo.saldo_final or 0
        saldo_calculado = periodo.saldo_calculado or 0
        diferencia = saldo_final - saldo_calculado
        # Diferencias abonos/cargos vs banco
        dif_ingresos = None
        dif_egresos = None
        if periodo.abonos_banco is not None:
            dif_ingresos = (movimientos['total_ingresos'] or 0) - periodo.abonos_banco
        if periodo.cargos_banco is not None:
            dif_egresos = (movimientos['total_egresos'] or 0) - periodo.cargos_banco

        periodos.append(
            {
                "cuenta": cuenta,
                "periodo": periodo,
                "movimientos": movimientos,
                "diferencia": diferencia,
                "dif_ingresos": dif_ingresos,
                "dif_egresos": dif_egresos,
            }
        )

    anios = range(hoy.year - 3, hoy.year + 1)
    meses = range(1, 13)

    return render(
        request,
        "conciliacion/saldos_periodo.html",
        {
            "periodos": periodos,
            "empresa": empresa,
            "anio": anio,
            "mes": mes,
            "anios": anios,
            "meses": meses,
        },
    )


@login_required
def cerrar_periodo(request, periodo_id):
    es_super = request.user.is_superuser
    if es_super:
        empresa_id = request.session.get("empresa_id")
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = request.user.perfilusuario.empresa

    periodo = get_object_or_404(SaldoCuentaPeriodo, pk=periodo_id, empresa=empresa)

    if periodo.cerrado:
        messages.warning(request, "Este período ya está cerrado.")
        return redirect("conciliaciones:saldos_periodo")

    if request.method == "POST":
        saldo_final_banco = request.POST.get("saldo_final_banco")
        notas = request.POST.get("notas", "")
        abonos_banco = request.POST.get("abonos_banco")
        cargos_banco = request.POST.get("cargos_banco")

        try:
            saldo_final_banco = Decimal(saldo_final_banco)
            periodo.abonos_banco = Decimal(abonos_banco) if abonos_banco else None
            periodo.cargos_banco = Decimal(cargos_banco) if cargos_banco else None
        except Exception:
            messages.error(request, "Valores inválidos.")
            return redirect("conciliaciones:saldos_periodo")

        periodo.saldo_final = saldo_final_banco
        periodo.cerrado = True
        periodo.fecha_cierre = timezone.now()
        periodo.cerrado_por = request.user
        periodo.notas = notas
        periodo.save()

        messages.success(
            request,
            f"Período {periodo.nombre_mes()} {periodo.anio} cerrado correctamente.",
        )
        return redirect("conciliaciones:saldos_periodo")
    
    movimientos = calcular_saldo_cuenta_periodo(periodo.cuenta, periodo.anio, periodo.mes)

    return render(request, "conciliacion/cerrar_periodo.html", {"periodo": periodo,"movimientos": movimientos,})
