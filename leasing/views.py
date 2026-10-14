"""Pantallas del ERP inmobiliario (segmento 'arrendamiento').

Todas las consultas se filtran por la empresa del usuario (``.de_empresa``). Las acciones
(activar, aprobar, generar calendario) son POST, validan permisos de Django y quedan en la
bitácora de auditoría.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .access import leasing_view
from .models import (
    BitacoraAuditoria,
    Contrato,
    ContratoVersion,
    Garantia,
    Incidencia,
    Obligacion,
    PartidaCalendario,
)
from .services.calendario import generar_calendario, mas_meses

ROLES_INGRESO = ("INGRESO", "SUBARRIENDO")


def _bitacora(request, accion, entidad, entidad_id, anterior=None, nuevo=None, motivo=""):
    BitacoraAuditoria.objects.create(
        empresa=request.empresa_leasing, usuario=request.user, accion=accion, entidad=entidad,
        entidad_id=str(entidad_id), valor_anterior=anterior, valor_nuevo=nuevo, motivo=motivo,
        ip=request.META.get("REMOTE_ADDR") or None,
    )


def _volver(request, defecto):
    destino = request.POST.get("next") or ""
    if destino.startswith("/leasing/") and url_has_allowed_host_and_scheme(destino, request.get_host()):
        return redirect(destino)
    return redirect(defecto)


def _suma(qs):
    return qs.aggregate(t=Sum("monto"))["t"] or Decimal("0")


# --------------------------------------------------------------------------
# Inicio
# --------------------------------------------------------------------------
@leasing_view()
def inicio(request):
    e = request.empresa_leasing
    hoy = date.today()
    mes_ini = hoy.replace(day=1)
    mes_sig = mas_meses(mes_ini, 1)

    contratos = Contrato.objects.de_empresa(e)
    partidas = PartidaCalendario.objects.de_empresa(e).exclude(estado="CANCELADA")
    del_mes = partidas.filter(periodo__gte=mes_ini, periodo__lt=mes_sig)

    por_vencer = (
        ContratoVersion.objects.de_empresa(e)
        .filter(es_vigente=True, contrato__estado__in=["ACTIVO", "EN_RENOVACION"],
                fecha_fin__range=(hoy, hoy + timedelta(days=90)))
        .select_related("contrato").order_by("fecha_fin")
    )
    por_aprobar = (
        partidas.filter(estado="PROYECTADA", fecha_vencimiento__lte=hoy + timedelta(days=30))
        .select_related("contrato", "termino__concepto").order_by("fecha_vencimiento")
    )
    obligaciones = [
        o for o in Obligacion.objects.de_empresa(e)
        .filter(estado__in=["PENDIENTE", "VENCIDA"], fecha_limite__lte=hoy + timedelta(days=365))
        .select_related("contrato")[:200]
        if (o.fecha_limite - hoy).days <= o.dias_anticipacion_alerta
    ]
    garantias = (
        Garantia.objects.de_empresa(e)
        .filter(activa=True, vigencia_fin__isnull=False, vigencia_fin__lte=hoy + timedelta(days=60))
        .select_related("contrato").order_by("vigencia_fin")
    )
    inc = Incidencia.objects.de_empresa(e).filter(estado__in=["ABIERTA", "EN_PROCESO"])

    ctx = {
        "empresa": e,
        "kpi": {
            "activos": contratos.filter(estado="ACTIVO").count(),
            "borradores": contratos.filter(estado="BORRADOR").count(),
            "ingresos_mes": _suma(del_mes.filter(contrato__rol__in=ROLES_INGRESO)),
            "egresos_mes": _suma(del_mes.filter(contrato__rol="EGRESO")),
            "por_vencer": por_vencer.count(),
            "por_aprobar": por_aprobar.count(),
            "incidencias": inc.count(),
            "urgentes": inc.filter(prioridad="URGENTE").count(),
        },
        "mes": mes_ini,
        "lista_vencer": por_vencer[:8],
        "lista_aprobar": por_aprobar[:8],
        "lista_obligaciones": obligaciones[:8],
        "lista_garantias": garantias[:8],
        "hoy": hoy,
        "seccion": "inicio",
    }
    return render(request, "leasing/inicio.html", ctx)


# --------------------------------------------------------------------------
# Contratos
# --------------------------------------------------------------------------
@leasing_view()
def contratos_lista(request):
    e = request.empresa_leasing
    q = (request.GET.get("q") or "").strip()
    rol = request.GET.get("rol") or ""
    estado = request.GET.get("estado") or ""

    qs = Contrato.objects.de_empresa(e)
    if rol in dict(Contrato.Rol.choices):
        qs = qs.filter(rol=rol)
    if estado in dict(Contrato.Estado.choices):
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(
            Q(folio__icontains=q)
            | Q(partes__contraparte__razon_social__icontains=q)
            | Q(versiones__unidades__unidad__clave__icontains=q)
            | Q(versiones__unidades__unidad__inmueble__nombre__icontains=q)
        ).distinct()
    qs = qs.prefetch_related(
        "versiones__unidades__unidad__inmueble", "versiones__terminos__concepto", "partes__contraparte"
    ).order_by("folio")

    pagina = Paginator(qs, 25).get_page(request.GET.get("page"))
    filas = []
    for c in pagina:
        v = next((x for x in c.versiones.all() if x.es_vigente), None)
        unidad = next(iter(v.unidades.all()), None) if v else None
        renta = None
        if v:
            for t in v.terminos.all():
                if t.concepto.tipo == "RENTA":
                    renta = t.monto
                    break
        contraparte = next(
            (p.contraparte for p in c.partes.all()
             if p.rol_parte == ("ARRENDADOR" if c.rol == "EGRESO" else "ARRENDATARIO")),
            None,
        )
        filas.append({"c": c, "v": v, "unidad": unidad.unidad if unidad else None,
                      "renta": renta, "contraparte": contraparte})

    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "leasing/contratos.html", {
        "empresa": e, "pagina": pagina, "filas": filas, "q": q, "rol": rol, "estado": estado,
        "roles": Contrato.Rol.choices, "estados": Contrato.Estado.choices,
        "qs_filtros": params.urlencode(), "seccion": "contratos",
    })


@leasing_view()
def contrato_detalle(request, pk):
    e = request.empresa_leasing
    c = get_object_or_404(Contrato.objects.de_empresa(e), pk=pk)
    v = c.version_vigente
    hoy = date.today()

    terminos = (v.terminos.select_related("concepto").prefetch_related("escaladores") if v else [])
    unidades = (v.unidades.select_related("unidad__inmueble") if v else [])
    m2_total = sum((u.m2_asignados for u in unidades), Decimal("0"))

    maestro = c.maestro if c.rol == "SUBARRIENDO" else None
    relacion = getattr(c, "relacion_maestro", None) if c.rol == "SUBARRIENDO" else None
    subs = []
    m2_subs = Decimal("0")
    if c.rol == "EGRESO":
        subs = list(c.relaciones_sub.select_related("sub").all())
        m2_subs = sum((r.m2_asignados for r in subs), Decimal("0"))

    partidas = list(c.partidas.select_related("termino__concepto").order_by("periodo", "id"))
    proxima = next((p for p in partidas if p.periodo >= hoy.replace(day=1)), None)
    hasta_default = min(filter(None, [v.fecha_fin if v else None, mas_meses(hoy, 24)])) if v else hoy

    puede_activar, motivo_activar = c.puede_activarse() if c.estado == "BORRADOR" else (False, "")
    u = request.user
    return render(request, "leasing/contrato_detalle.html", {
        "empresa": e, "c": c, "v": v, "versiones": c.versiones.order_by("-numero"),
        "partes": c.partes.select_related("contraparte"), "terminos": terminos, "unidades": unidades,
        "m2_total": m2_total, "maestro": maestro, "relacion": relacion, "subs": subs, "m2_subs": m2_subs,
        "garantias": c.garantias.filter(activa=True), "obligaciones": c.obligaciones.all()[:10],
        "documentos": c.documentos.order_by("-creado_en")[:8], "partidas": partidas, "proxima": proxima,
        "hasta_default": hasta_default, "hoy": hoy,
        "puede_activar": puede_activar, "motivo_activar": motivo_activar,
        "perm_activar": u.has_perm("leasing.change_contrato"),
        "perm_generar": u.has_perm("leasing.add_partidacalendario"),
        "perm_aprobar": u.has_perm("leasing.change_partidacalendario"),
        "seccion": "contratos",
    })


@require_POST
@leasing_view("leasing.change_contrato")
def contrato_activar(request, pk):
    c = get_object_or_404(Contrato.objects.de_empresa(request.empresa_leasing), pk=pk)
    anterior = c.estado
    try:
        c.activar()
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        _bitacora(request, "ACTIVAR", "Contrato", c.pk, {"estado": anterior}, {"estado": c.estado})
        messages.success(request, f"Contrato {c.folio} activado.")
    return redirect("leasing:contrato", pk=c.pk)


@require_POST
@leasing_view("leasing.add_partidacalendario")
def contrato_generar_calendario(request, pk):
    c = get_object_or_404(Contrato.objects.de_empresa(request.empresa_leasing), pk=pk)
    v = c.version_vigente
    try:
        hasta = date.fromisoformat(request.POST.get("hasta", ""))
    except ValueError:
        messages.error(request, "Fecha inválida.")
        return redirect("leasing:contrato", pk=c.pk)
    if not v or not v.terminos.exists():
        messages.error(request, "El contrato no tiene términos financieros en su versión vigente.")
        return redirect("leasing:contrato", pk=c.pk)
    creadas = actualizadas = 0
    pendientes = []
    for t in v.terminos.select_related("version__contrato", "empresa"):
        r = generar_calendario(t, hasta, usuario=request.user)
        creadas += r.creadas
        actualizadas += r.actualizadas
        pendientes += r.pendientes
    messages.success(request, f"Calendario generado: {creadas} nuevas, {actualizadas} actualizadas.")
    for p in dict.fromkeys(pendientes):
        messages.warning(request, "Pendiente: " + p)
    return redirect("leasing:contrato", pk=c.pk)


# --------------------------------------------------------------------------
# Calendario de rentas (todos los contratos)
# --------------------------------------------------------------------------
@leasing_view()
def calendario(request):
    e = request.empresa_leasing
    hoy = date.today()
    try:
        y, m = (request.GET.get("mes") or hoy.strftime("%Y-%m")).split("-")
        mes = date(int(y), int(m), 1)
    except ValueError:
        mes = hoy.replace(day=1)
    estado = request.GET.get("estado") or ""
    sentido = request.GET.get("sentido") or ""

    qs = PartidaCalendario.objects.de_empresa(e).filter(periodo__gte=mes, periodo__lt=mas_meses(mes, 1))
    if estado in dict(PartidaCalendario.Estado.choices):
        qs = qs.filter(estado=estado)
    if sentido == "ingresos":
        qs = qs.filter(contrato__rol__in=ROLES_INGRESO)
    elif sentido == "egresos":
        qs = qs.filter(contrato__rol="EGRESO")
    qs = qs.select_related("contrato", "termino__concepto")

    base = PartidaCalendario.objects.de_empresa(e).filter(
        periodo__gte=mes, periodo__lt=mas_meses(mes, 1)).exclude(estado="CANCELADA")
    return render(request, "leasing/calendario.html", {
        "empresa": e, "partidas": qs.order_by("fecha_vencimiento", "contrato__folio")[:300],
        "mes": mes, "mes_ant": mas_meses(mes, -1), "mes_sig": mas_meses(mes, 1), "estado": estado,
        "sentido": sentido, "estados": PartidaCalendario.Estado.choices,
        "total_ingresos": _suma(base.filter(contrato__rol__in=ROLES_INGRESO)),
        "total_egresos": _suma(base.filter(contrato__rol="EGRESO")),
        "perm_aprobar": request.user.has_perm("leasing.change_partidacalendario"),
        "seccion": "calendario",
    })


@require_POST
@leasing_view("leasing.change_partidacalendario")
def partida_aprobar(request, pk):
    p = get_object_or_404(PartidaCalendario.objects.de_empresa(request.empresa_leasing), pk=pk)
    anterior = p.estado
    try:
        p.aprobar(request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        _bitacora(request, "APROBAR_PARTIDA", "PartidaCalendario", p.pk,
                  {"estado": anterior}, {"estado": p.estado, "monto": str(p.monto)})
        messages.success(request, f"Renta {p.periodo:%m/%Y} del contrato {p.contrato.folio} aprobada.")
    return _volver(request, "leasing:calendario")


# --------------------------------------------------------------------------
# Incidencias / mantenimiento
# --------------------------------------------------------------------------
@leasing_view()
def incidencias(request):
    e = request.empresa_leasing
    estado = request.GET.get("estado") or "abiertas"
    prioridad = request.GET.get("prioridad") or ""
    qs = Incidencia.objects.de_empresa(e).select_related("inmueble", "unidad", "proveedor", "contrato")
    if estado == "abiertas":
        qs = qs.filter(estado__in=["ABIERTA", "EN_PROCESO"])
    elif estado in dict(Incidencia.Estado.choices):
        qs = qs.filter(estado=estado)
    if prioridad in dict(Incidencia.Prioridad.choices):
        qs = qs.filter(prioridad=prioridad)
    resumen = {
        r["naturaleza_gasto"]: r
        for r in qs.values("naturaleza_gasto").annotate(n=Count("id"), est=Sum("costo_estimado"), real=Sum("costo_real"))
    }
    return render(request, "leasing/incidencias.html", {
        "empresa": e, "incidencias": qs.order_by("-fecha_reporte")[:200], "estado": estado,
        "prioridad": prioridad, "estados": Incidencia.Estado.choices,
        "prioridades": Incidencia.Prioridad.choices, "resumen": resumen, "seccion": "incidencias",
    })
