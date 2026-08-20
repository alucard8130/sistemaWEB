# ============================================================
# cobranza/views.py -- parte 1: Dashboard + apertura automática
# ============================================================

import datetime
from calendar import calendar
from decimal import ROUND_DOWN, Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from acceso_empresas.decorators import login_o_portal_required
from empleados.models import Empleado
from facturacion.models import Factura
from sanitarios.views import _empresa_actual

from .models import (
    ExpedienteCobranza,
    GestionCobranza,
    ParcialidadPlanPago,
    PlanDePago,
    PlantillaCobranza,
)
from django.db.models import Sum


# ============================================================
# Detección automática -- abre un expediente para cualquier cliente
# con saldo vencido que todavía no tenga uno activo. Corre este
# comando diario (mismo Cron que ya usas para otras tareas).
# ============================================================


def detectar_y_abrir_expedientes(empresa):
    hoy = timezone.now().date()
    # NUEVO -- solo cuenta como "candidato a expediente" si el atraso es
    # de MÁS de 30 días -- un adeudo reciente (30 días o menos) todavía
    # no abre expediente de cobranza.
    limite_30_dias = hoy - datetime.timedelta(days=30)

    
    clientes_con_vencidas = set(
        Factura.objects.filter(
            empresa=empresa,
            activo=True,
            estatus="pendiente",
            fecha_vencimiento__lt=limite_30_dias,monto__gt=0,
        ).values_list("cliente_id", flat=True)
    )

    clientes_con_expediente_activo = set(
        ExpedienteCobranza.objects.filter(
            empresa=empresa,
            estatus="activo",
        ).values_list("cliente_id", flat=True)
    )

    nuevos = clientes_con_vencidas - clientes_con_expediente_activo
    creados = 0
    for cliente_id in nuevos:
        ExpedienteCobranza.objects.create(empresa=empresa, cliente_id=cliente_id)
        creados += 1
    return creados


# ============================================================
# NUEVO -- agrega esta función en cobranza/views.py, junto a las demás
# ============================================================


def _precomputar_saldos_expedientes(expedientes_lista, empresa):
    """
    Calcula saldo_vencido_total y dias_atraso_maximo para TODOS los
    expedientes de la lista, usando solo 2 consultas totales (con sus
    prefetch de pagos/cobros) -- en vez de 2 consultas POR expediente.

    "Primea" el caché de cached_property directamente en cada instancia,
    así que después de llamar esta función, leer
    expediente.saldo_vencido_total / expediente.dias_atraso_maximo
    en cualquier parte (vista o template) ya no toca la base de datos.
    """

    hoy = timezone.now().date()
    cliente_ids = [e.cliente_id for e in expedientes_lista]

    # UNA consulta (+ 1 de prefetch) para TODAS las facturas vencidas de
    # TODOS los clientes con expediente, en vez de una por cliente.
    facturas = Factura.objects.filter(
        empresa=empresa,
        cliente_id__in=cliente_ids,
        activo=True,
        estatus="pendiente",
        fecha_vencimiento__lt=hoy,
    ).prefetch_related("pagos")

    # Agrupa en Python (rápido, ya está todo en memoria -- sin más
    # consultas, gracias al prefetch_related de arriba)
    por_cliente = {}
    for f in facturas:
        d = por_cliente.setdefault(f.cliente_id, {"saldo": Decimal("0"), "fechas": []})  # noqa: FURB157
        d["saldo"] += Decimal(str(f.saldo_pendiente))
        d["fechas"].append(f.fecha_vencimiento)

    for exp in expedientes_lista:
        datos = por_cliente.get(exp.cliente_id, {"saldo": Decimal("0"), "fechas": []})  # noqa: FURB157
        saldo = datos["saldo"]
        dias = (hoy - min(datos["fechas"])).days if datos["fechas"] else 0

        # Primea el caché de cached_property directamente -- así,
        # cuando el resto del código lea exp.saldo_vencido_total o
        # exp.dias_atraso_maximo, ya no dispara ninguna consulta.
        exp.__dict__["saldo_vencido_total"] = saldo
        exp.__dict__["dias_atraso_maximo"] = dias


# ============================================================
# Dashboard de Cobranza
# ============================================================


@login_required
def dashboard_cobranza(request):
    empresa = _empresa_actual(request)  # mismo helper que ya usa el resto de GESAC
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")
 
    # Detecta clientes nuevos con deuda vencida cada vez que se visita
    # el dashboard -- respaldo por si el Cron diario no ha corrido.
    detectar_y_abrir_expedientes(empresa)
 
    etapa_filtro = request.GET.get("etapa")
    asignado_filtro = request.GET.get("asignado")
    antiguedad_filtro = request.GET.get("antiguedad")

    empleados_empresa = Empleado.objects.filter(empresa=empresa, activo=True).order_by('nombre')

    expedientes = ExpedienteCobranza.objects.filter(
        empresa=empresa, estatus='activo'
    ).select_related('cliente', 'asignado_a')
 
    if etapa_filtro:
        expedientes = expedientes.filter(etapa=etapa_filtro)
    if asignado_filtro:
        expedientes = expedientes.filter(asignado_a_id=asignado_filtro)
 
    # El saldo/antigüedad se calcula en Python (son properties dinámicas,
    # no se pueden filtrar directo en SQL) -- para carteras muy grandes,
    # considera cachear esto en un job nocturno si se vuelve lento.
    expedientes_lista = list(expedientes)
 
    # NUEVO -- precalcula saldo/antigüedad de TODOS los expedientes con
    # solo 2 consultas totales, en vez de 2 por expediente. Debe ir
    # ANTES de cualquier .sort()/sum()/acceso a esas properties.
    _precomputar_saldos_expedientes(expedientes_lista, empresa)
 
    if antiguedad_filtro:
        expedientes_lista = [e for e in expedientes_lista if e.rango_antiguedad == antiguedad_filtro]
 
    expedientes_lista.sort(key=lambda e: e.dias_atraso_maximo, reverse=True)
 
    cartera_vencida_total = sum(e.saldo_vencido_total for e in expedientes_lista)
    total_expedientes = len(expedientes_lista)
 
    # Desglose por etapa, para las tarjetas del pipeline -- SIEMPRE sobre
    # la lista completa filtrada, no solo la página actual.
    por_etapa = {}
    for etapa_key, etapa_label in ExpedienteCobranza.ETAPA_CHOICES:
        en_esta_etapa = [e for e in expedientes_lista if e.etapa == etapa_key]
        por_etapa[etapa_key] = {
            "label": etapa_label,
            "cantidad": len(en_esta_etapa),
            "monto": sum(e.saldo_vencido_total for e in en_esta_etapa),
        }
 
    # NUEVO -- paginador, 20 por página. Va DESPUÉS de calcular los
    # totales/KPIs de arriba, que deben reflejar TODO lo filtrado, no
    # solo la página visible.
    paginator = Paginator(expedientes_lista, 20)
    expedientes_pagina = paginator.get_page(request.GET.get("page"))
 
    # Recordatorios de hoy -- gestiones con próxima acción vencida o de hoy
    recordatorios_hoy = GestionCobranza.objects.filter(
        expediente__empresa=empresa, proxima_accion_completada=False,
        proxima_accion_fecha__lte=timezone.now().date(),
    ).select_related('expediente', 'expediente__cliente').order_by('proxima_accion_fecha')
 
    return render(request, "gestion_cobranza/dashboard.html", {
        "empresa": empresa,
        "expedientes": expedientes_pagina,
        "cartera_vencida_total": cartera_vencida_total,
        "total_expedientes": total_expedientes,
        "por_etapa": por_etapa,
        "etapa_choices": ExpedienteCobranza.ETAPA_CHOICES,
        "etapa_filtro": etapa_filtro,
        "antiguedad_filtro": antiguedad_filtro,
        "recordatorios_hoy": recordatorios_hoy,
        "empleados_empresa": empleados_empresa,
    })


@login_required
def detalle_expediente(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(
        ExpedienteCobranza, id=expediente_id, empresa=empresa
    )

    gestiones = expediente.gestiones.select_related("registrado_por").all()
    facturas_vencidas = expediente._facturas_vencidas_lista
    planes_pago = expediente.planes_pago.prefetch_related("parcialidades").all()

    plantillas = PlantillaCobranza.objects.filter(empresa=empresa, activa=True)
    empleados_empresa = Empleado.objects.filter(empresa=empresa, activo=True).order_by('nombre')

    return render(
        request,
        "gestion_cobranza/detalle_expediente.html",
        {
            "empresa": empresa,
            "expediente": expediente,
            "gestiones": gestiones,
            "facturas_vencidas": facturas_vencidas,
            "planes_pago": planes_pago,
            "plantillas": plantillas,
            "tipo_choices": GestionCobranza.TIPO_CHOICES,
            "resultado_choices": GestionCobranza.RESULTADO_CHOICES,
            "etapa_choices": ExpedienteCobranza.ETAPA_CHOICES,
            "empleados_empresa": empleados_empresa,
        },
    )


@login_required
def registrar_gestion(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(
        ExpedienteCobranza, id=expediente_id, empresa=empresa
    )

    if request.method != "POST":
        return redirect("detalle_expediente", expediente_id=expediente.id)

    tipo_gestion = request.POST.get("tipo_gestion")
    resultado = request.POST.get("resultado")
    notas = request.POST.get("notas", "").strip()
    proxima_accion_fecha = request.POST.get("proxima_accion_fecha") or None
    proxima_accion_descripcion = request.POST.get(
        "proxima_accion_descripcion", ""
    ).strip()

    if tipo_gestion not in dict(GestionCobranza.TIPO_CHOICES):
        messages.error(request, "Selecciona un tipo de gestión válido.")
        return redirect("detalle_expediente", expediente_id=expediente.id)

    GestionCobranza.objects.create(
        expediente=expediente,
        tipo_gestion=tipo_gestion,
        resultado=resultado or "pendiente_respuesta",
        notas=notas,
        registrado_por=request.user,
        proxima_accion_fecha=proxima_accion_fecha,
        proxima_accion_descripcion=proxima_accion_descripcion or None,
    )

    # Si el resultado fue "ya_pago", sugiere cerrar el expediente
    if resultado == "ya_pago":
        messages.warning(
            request,
            "Marcaste esta gestión como 'Ya había pagado' -- si el saldo vencido ya está en $0, "
            "considera cerrar el expediente.",
        )
    else:
        messages.success(request, "Gestión registrada correctamente.")

    return redirect("detalle_expediente", expediente_id=expediente.id)


@login_required
def cambiar_etapa_expediente(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(
        ExpedienteCobranza, id=expediente_id, empresa=empresa
    )

    if request.method != "POST":
        return redirect("detalle_expediente", expediente_id=expediente.id)

    nueva_etapa = request.POST.get("etapa")
    if nueva_etapa not in dict(ExpedienteCobranza.ETAPA_CHOICES):
        messages.error(request, "Etapa inválida.")
        return redirect("detalle_expediente", expediente_id=expediente.id)

    etapa_anterior = expediente.get_etapa_display()
    expediente.etapa = nueva_etapa
    expediente.save(update_fields=["etapa"])

    # Deja registro del cambio de etapa como una gestión tipo "nota"
    GestionCobranza.objects.create(
        expediente=expediente,
        tipo_gestion="nota",
        resultado="otro",
        registrado_por=request.user,
        notas=f'Etapa cambiada de "{etapa_anterior}" a "{expediente.get_etapa_display()}".',
    )

    messages.success(request, f"Expediente movido a: {expediente.get_etapa_display()}")
    return redirect("detalle_expediente", expediente_id=expediente.id)


@login_required
def cerrar_expediente(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(
        ExpedienteCobranza, id=expediente_id, empresa=empresa
    )

    if request.method != "POST":
        return redirect("detalle_expediente", expediente_id=expediente.id)

    motivo = request.POST.get("motivo", "").strip()

    if (
        expediente.saldo_vencido_total > 0
        and request.POST.get("confirmar_con_saldo") != "1"
    ):
        messages.warning(
            request,
            f"Este expediente todavía tiene ${expediente.saldo_vencido_total:,.2f} de saldo vencido. "
            f"Si de verdad quieres cerrarlo así (por ejemplo, se turnó a jurídico externo), "
            f"marca la casilla de confirmación y guarda de nuevo.",
        )
        return redirect("detalle_expediente", expediente_id=expediente.id)

    expediente.cerrar(motivo=motivo)
    GestionCobranza.objects.create(
        expediente=expediente,
        tipo_gestion="nota",
        resultado="otro",
        registrado_por=request.user,
        notas=f"Expediente cerrado. Motivo: {motivo or 'Sin especificar'}",
    )

    messages.success(request, "Expediente cerrado correctamente.")
    return redirect("dashboard_cobranza")



# Cada función regresa (exitoso: bool, id_externo: str|None, error: str|None)
# -- mismo formato para los 3 canales, listo para guardar directo en
# GestionCobranza.envio_exitoso / envio_id_externo / envio_error.
# ============================================================


def _normalizar_telefono_mx(telefono):
    """Limpia el teléfono y le agrega +52 si hace falta -- Twilio exige
    formato E.164 (+52XXXXXXXXXX)."""
    if not telefono:
        return None
    digitos = "".join(c for c in telefono if c.isdigit())
    if not digitos:
        return None
    if len(digitos) == 10:
        return f"+52{digitos}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return f"+{digitos}"
    if len(digitos) == 13 and digitos.startswith("521"):
        return f"+{digitos}"
    return f"+{digitos}"


def enviar_whatsapp(empresa, telefono_destino, mensaje):
    if not (empresa.twilio_account_sid and empresa.twilio_auth_token and empresa.twilio_whatsapp_number):
        return False, None, "Esta empresa no tiene configurada su cuenta de Twilio para WhatsApp."

    destino = _normalizar_telefono_mx(telefono_destino)
    if not destino:
        return False, None, "El cliente no tiene un teléfono válido registrado."

    try:
        client = Client(empresa.twilio_account_sid, empresa.twilio_auth_token)
        msg = client.messages.create(
            from_=f"whatsapp:{empresa.twilio_whatsapp_number}",
            body=mensaje,
            to=f"whatsapp:{destino}",
        )
        return True, msg.sid, None
    except TwilioRestException as e:
        return False, None, str(e)
    except Exception as e:  # noqa: BLE001
        return False, None, f"Error inesperado: {e}"


def enviar_sms(empresa, telefono_destino, mensaje):
    if not (empresa.twilio_account_sid and empresa.twilio_auth_token and empresa.twilio_sms_number):
        return False, None, "Esta empresa no tiene configurada su cuenta de Twilio para SMS."

    destino = _normalizar_telefono_mx(telefono_destino)
    if not destino:
        return False, None, "El cliente no tiene un teléfono válido registrado."

    try:
        client = Client(empresa.twilio_account_sid, empresa.twilio_auth_token)
        msg = client.messages.create(
            from_=empresa.twilio_sms_number,
            body=mensaje,
            to=destino,
        )
        return True, msg.sid, None
    except TwilioRestException as e:
        return False, None, str(e)
    except Exception as e:  # noqa: BLE001
        return False, None, f"Error inesperado: {e}"


def enviar_email(empresa, email_destino, asunto, cuerpo):
    if not email_destino:
        return False, None, "El cliente no tiene un correo registrado."

    try:
        send_mail(
            subject=asunto or f"Aviso de {empresa.nombre}",
            message=cuerpo,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email_destino],
            fail_silently=False,
        )
        return True, None, None
    except Exception as e:  # noqa: BLE001
        return False, None, f"Error al enviar correo: {e}"


# ============================================================
# cobranza/views.py -- parte 3: envío de mensajes
# ============================================================


def enviar_mensaje_plantilla(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(ExpedienteCobranza, id=expediente_id, empresa=empresa)
 
    if request.method != "POST":
        return redirect("detalle_expediente", expediente_id=expediente.id)
 
    plantilla_id = request.POST.get("plantilla_id")
    plantilla = get_object_or_404(PlantillaCobranza, id=plantilla_id, empresa=empresa, activa=True)
 
    if plantilla.canal == "carta_extrajudicial":
        messages.info(request, "Las cartas extrajudiciales se descargan como PDF -- usa el botón correspondiente en el expediente, no el de enviar.")
        return redirect("detalle_expediente", expediente_id=expediente.id)
 
    asunto, cuerpo = plantilla.renderizar(expediente)
 
    if plantilla.canal == "whatsapp":
        exitoso, id_externo, error = enviar_whatsapp(empresa, expediente.cliente.telefono, cuerpo)
        tipo_gestion = "whatsapp"
    elif plantilla.canal == "sms":
        exitoso, id_externo, error = enviar_sms(empresa, expediente.cliente.telefono, cuerpo)
        tipo_gestion = "sms"
    elif plantilla.canal == "email":
        exitoso, id_externo, error = enviar_email(empresa, expediente.cliente.email, asunto, cuerpo)
        tipo_gestion = "email"
    else:
        messages.error(request, "Canal de plantilla no reconocido.")
        return redirect("detalle_expediente", expediente_id=expediente.id)
 
    # Se registra en la bitácora SIEMPRE, haya funcionado o no -- para
    # tener rastro de los intentos fallidos también.
    GestionCobranza.objects.create(
        expediente=expediente, tipo_gestion=tipo_gestion, resultado="pendiente_respuesta",
        registrado_por=request.user, mensaje_enviado=cuerpo,
        envio_exitoso=exitoso, envio_id_externo=id_externo, envio_error=error,
        notas=f'Enviado usando la plantilla "{plantilla.nombre}".',
    )
 
    if exitoso:
        messages.success(request, f"{plantilla.get_canal_display()} enviado correctamente.")
    else:
        messages.error(request, f"No se pudo enviar: {error}")
 
    return redirect("detalle_expediente", expediente_id=expediente.id)

# ============================================================
# cobranza/views.py -- parte 4: administración de Plantillas
# ============================================================

@login_required
def lista_plantillas(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    plantillas = PlantillaCobranza.objects.filter(empresa=empresa).order_by('canal', 'nombre')

    return render(request, "gestion_cobranza/lista_plantillas.html", {
        "empresa": empresa,
        "plantillas": plantillas,
    })


@login_required
def crear_plantilla(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        canal = request.POST.get("canal")
        nombre = request.POST.get("nombre", "").strip()
        etapa_sugerida = request.POST.get("etapa_sugerida") or None
        asunto = request.POST.get("asunto", "").strip()
        cuerpo = request.POST.get("cuerpo", "").strip()

        if canal not in dict(PlantillaCobranza.CANAL_CHOICES):
            messages.error(request, "Selecciona un canal válido.")
            return redirect("crear_plantilla")
        if not nombre or not cuerpo:
            messages.error(request, "El nombre y el cuerpo del mensaje son obligatorios.")
            return redirect("crear_plantilla")

        PlantillaCobranza.objects.create(
            empresa=empresa, canal=canal, nombre=nombre,
            etapa_sugerida=etapa_sugerida, asunto=asunto or None, cuerpo=cuerpo,
        )
        messages.success(request, f'Plantilla "{nombre}" creada correctamente.')
        return redirect("lista_plantillas")

    return render(request, "gestion_cobranza/form_plantilla.html", {
        "empresa": empresa,
        "modo": "crear",
        "canal_choices": PlantillaCobranza.CANAL_CHOICES,
        "etapa_choices": ExpedienteCobranza.ETAPA_CHOICES,
    })


@login_required
def editar_plantilla(request, plantilla_id):
    empresa = _empresa_actual(request)
    plantilla = get_object_or_404(PlantillaCobranza, id=plantilla_id, empresa=empresa)

    if request.method == "POST":
        canal = request.POST.get("canal")
        nombre = request.POST.get("nombre", "").strip()
        etapa_sugerida = request.POST.get("etapa_sugerida") or None
        asunto = request.POST.get("asunto", "").strip()
        cuerpo = request.POST.get("cuerpo", "").strip()

        if canal not in dict(PlantillaCobranza.CANAL_CHOICES):
            messages.error(request, "Selecciona un canal válido.")
            return redirect("editar_plantilla", plantilla_id=plantilla.id)
        if not nombre or not cuerpo:
            messages.error(request, "El nombre y el cuerpo del mensaje son obligatorios.")
            return redirect("editar_plantilla", plantilla_id=plantilla.id)

        plantilla.canal = canal
        plantilla.nombre = nombre
        plantilla.etapa_sugerida = etapa_sugerida
        plantilla.asunto = asunto or None
        plantilla.cuerpo = cuerpo
        plantilla.save()

        messages.success(request, "Plantilla actualizada correctamente.")
        return redirect("lista_plantillas")

    return render(request, "gestion_cobranza/form_plantilla.html", {
        "empresa": empresa,
        "modo": "editar",
        "plantilla": plantilla,
        "canal_choices": PlantillaCobranza.CANAL_CHOICES,
        "etapa_choices": ExpedienteCobranza.ETAPA_CHOICES,
    })


@login_required
def toggle_activa_plantilla(request, plantilla_id):
    empresa = _empresa_actual(request)
    plantilla = get_object_or_404(PlantillaCobranza, id=plantilla_id, empresa=empresa)

    if request.method != "POST":
        return redirect("lista_plantillas")

    plantilla.activa = not plantilla.activa
    plantilla.save(update_fields=["activa"])

    estado = "activada" if plantilla.activa else "desactivada"
    messages.success(request, f'Plantilla "{plantilla.nombre}" {estado}.')
    return redirect("lista_plantillas")


# ============================================================
# parte 5: carta extrajudicial en PDF
# ===========================================================

@login_required
def generar_carta_extrajudicial_pdf(request, expediente_id, plantilla_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(ExpedienteCobranza, id=expediente_id, empresa=empresa)
    plantilla = get_object_or_404(
        PlantillaCobranza, id=plantilla_id, empresa=empresa,
        canal="carta_extrajudicial", activa=True,
    )

    _, cuerpo = plantilla.renderizar(expediente)
    facturas = expediente._facturas_vencidas_lista

    # ---- Construcción del PDF ----
    response = HttpResponse(content_type="application/pdf")
    nombre_archivo = f"carta_extrajudicial_{expediente.cliente.nombre.replace(' ', '_')}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'

    doc = SimpleDocTemplate(
        response, pagesize=letter,
        topMargin=2.5 * cm, bottomMargin=2.5 * cm, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloCarta", parent=styles["Heading1"], fontSize=15, alignment=1, spaceAfter=6,
    )
    estilo_normal = ParagraphStyle(
        "NormalCarta", parent=styles["Normal"], fontSize=10.5, leading=16, spaceAfter=12,
    )
    estilo_fecha = ParagraphStyle(
        "FechaCarta", parent=styles["Normal"], fontSize=10, alignment=2, spaceAfter=18,
    )
    estilo_firma = ParagraphStyle(
        "FirmaCarta", parent=styles["Normal"], fontSize=10, alignment=1, spaceBefore=40,
    )

    story = []

    # Membrete
    story.append(Paragraph(empresa.nombre, ParagraphStyle("Membrete", parent=styles["Heading2"], fontSize=13, spaceAfter=2)))
    if getattr(empresa, "direccion", None):
        story.append(Paragraph(str(empresa.direccion), ParagraphStyle("Dir", parent=styles["Normal"], fontSize=8.5, textColor=colors.grey)))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#5a0000")))
    story.append(Spacer(1, 16))

    # Fecha -- meses en español fijos, sin depender del locale del
    # servidor (que puede no tener es_MX instalado en producción).
    from django.utils import timezone
    MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    hoy = timezone.now()
    fecha_texto = f"{hoy.day} de {MESES_ES[hoy.month - 1]} de {hoy.year}"
    story.append(Paragraph(fecha_texto, estilo_fecha))

    # Título
    story.append(Paragraph("AVISO EXTRAJUDICIAL DE COBRO", estilo_titulo))
    story.append(Spacer(1, 6))

    # Destinatario
    story.append(Paragraph(f"<b>A:</b> {expediente.cliente.nombre}", estilo_normal))
    if expediente.cliente.direccion_domicilio:
        story.append(Paragraph(f"<b>Domicilio:</b> {expediente.cliente.direccion_domicilio}", estilo_normal))
    story.append(Spacer(1, 10))

    # Cuerpo (texto de la plantilla, con placeholders ya sustituidos)
    for parrafo in cuerpo.split("\n"):
        if parrafo.strip():
            story.append(Paragraph(parrafo.strip(), estilo_normal))

    story.append(Spacer(1, 14))

    # Tabla de facturas vencidas
    if facturas:
        data = [["Folio", "Concepto", "Vencimiento", "Saldo"]]
        for f in facturas:
            origen = "—"
            if f.local:
                origen = f"Local {f.local.numero}"
            elif f.area_comun:
                origen = f"Área {f.area_comun.numero}"
            data.append([
                f.folio, origen, f.fecha_vencimiento.strftime("%d/%m/%Y"),
                f"${f.saldo_pendiente:,.2f}",
            ])
        data.append(["", "", "TOTAL", f"${expediente.saldo_vencido_total:,.2f}"])

        tabla = Table(data, colWidths=[3.2 * cm, 4.3 * cm, 3.2 * cm, 3.3 * cm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5a0000")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f8f8")]),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#5a0000")),
        ]))
        story.append(tabla)
        story.append(Spacer(1, 20))

    # Firma
    story.append(Paragraph("Atentamente,", estilo_firma))
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 40, ParagraphStyle("Linea", parent=styles["Normal"], alignment=1)))
    story.append(Paragraph(empresa.nombre, ParagraphStyle("NombreFirma", parent=styles["Normal"], alignment=1, fontSize=9.5, spaceBefore=4)))

    doc.build(story)

    # Deja registro del envío/generación en la bitácora
    GestionCobranza.objects.create(
        expediente=expediente, tipo_gestion="carta_extrajudicial", resultado="pendiente_respuesta",
        registrado_por=request.user, mensaje_enviado=cuerpo,
        envio_exitoso=True,
        notas=f'Carta extrajudicial generada usando la plantilla "{plantilla.nombre}".',
    )

    return response


# ============================================================
# cobranza/views.py -- parte 6: Plan de Pago
# ============================================================


@login_required
def crear_plan_pago(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(ExpedienteCobranza, id=expediente_id, empresa=empresa)

    if request.method == "POST":
        monto_total_raw = request.POST.get("monto_total", "").strip()
        numero_parcialidades_raw = request.POST.get("numero_parcialidades", "").strip()
        fecha_primera_str = request.POST.get("fecha_primera_parcialidad", "").strip()
        notas = request.POST.get("notas", "").strip()
        comprobante = request.FILES.get("comprobante_acuerdo")

        try:
            monto_total = Decimal(monto_total_raw)
            if monto_total <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Captura un monto total válido, mayor a $0.")
            return redirect("crear_plan_pago", expediente_id=expediente.id)

        try:
            numero_parcialidades = int(numero_parcialidades_raw)
            if numero_parcialidades < 1:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Captura un número de parcialidades válido (mínimo 1).")
            return redirect("crear_plan_pago", expediente_id=expediente.id)

        try:
            fecha_primera = datetime.date.fromisoformat(fecha_primera_str)
        except (ValueError, TypeError):
            messages.error(request, "Fecha de la primera parcialidad inválida.")
            return redirect("crear_plan_pago", expediente_id=expediente.id)

        with transaction.atomic():
            plan = PlanDePago.objects.create(
                expediente=expediente, monto_total=monto_total,
                numero_parcialidades=numero_parcialidades,
                creado_por=request.user, notas=notas, comprobante_acuerdo=comprobante,
            )

            # Reparte el monto total en partes iguales -- el residuo por
            # redondeo se agrega a la ÚLTIMA parcialidad, para que la
            # suma exacta siempre cuadre con monto_total.
            base = (monto_total / numero_parcialidades).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            acumulado = Decimal("0")

            for i in range(1, numero_parcialidades + 1):
                fecha_venc = _sumar_meses(fecha_primera, i - 1)
                if i < numero_parcialidades:
                    monto_parcialidad = base
                    acumulado += base
                else:
                    monto_parcialidad = monto_total - acumulado

                ParcialidadPlanPago.objects.create(
                    plan=plan, numero=i, fecha_vencimiento=fecha_venc, monto=monto_parcialidad,
                )

            # Un plan de pago mueve el expediente a esa etapa automáticamente
            expediente.etapa = "plan_pago"
            expediente.save(update_fields=["etapa"])

            GestionCobranza.objects.create(
                expediente=expediente, tipo_gestion="nota", resultado="promesa_pago",
                registrado_por=request.user,
                notas=f"Plan de pago acordado: ${monto_total:,.2f} en {numero_parcialidades} parcialidades.",
            )

        messages.success(request, "Plan de pago creado correctamente.")
        return redirect("detalle_plan_pago", plan_id=plan.id)

    return render(request, "gestion_cobranza/form_plan_pago.html", {
        "empresa": empresa,
        "expediente": expediente,
    })


def _sumar_meses(fecha, meses):
    """Suma N meses a una fecha, ajustando el día si el mes destino tiene
    menos días (ej. 31 de enero + 1 mes -> 28/29 de febrero)."""
    mes_total = fecha.month - 1 + meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
    dia = min(fecha.day, ultimo_dia_mes)
    return datetime.date(anio, mes, dia)


@login_required
def detalle_plan_pago(request, plan_id):
    empresa = _empresa_actual(request)
    plan = get_object_or_404(PlanDePago, id=plan_id, expediente__empresa=empresa)
    parcialidades = plan.parcialidades.all()

    return render(request, "gestion_cobranza/detalle_plan_pago.html", {
        "empresa": empresa,
        "plan": plan,
        "parcialidades": parcialidades,
    })


@login_required
def marcar_parcialidad_pagada(request, parcialidad_id):
    empresa = _empresa_actual(request)
    parcialidad = get_object_or_404(
        ParcialidadPlanPago, id=parcialidad_id, plan__expediente__empresa=empresa
    )

    if request.method != "POST":
        return redirect("detalle_plan_pago", plan_id=parcialidad.plan.id)

    fecha_pago_str = request.POST.get("fecha_pago", "").strip()
    try:
        fecha_pago = datetime.date.fromisoformat(fecha_pago_str) if fecha_pago_str else timezone.now().date()
    except ValueError:
        fecha_pago = timezone.now().date()

    parcialidad.estatus = "pagada"
    parcialidad.fecha_pago = fecha_pago
    parcialidad.save(update_fields=["estatus", "fecha_pago"])

    plan = parcialidad.plan
    plan.actualizar_estatus()

    GestionCobranza.objects.create(
        expediente=plan.expediente, tipo_gestion="nota", resultado="promesa_pago",
        registrado_por=request.user,
        notas=f"Parcialidad {parcialidad.numero}/{plan.numero_parcialidades} marcada como pagada (${parcialidad.monto:,.2f}).",
    )

    if plan.estatus == "cumplido":
        messages.success(request, "¡Parcialidad registrada! El plan de pago quedó completamente cumplido.")
    else:
        messages.success(request, "Parcialidad marcada como pagada.")

    return redirect("detalle_plan_pago", plan_id=plan.id)


# ============================================================
# cobranza/views.py -- parte 7: asignar expediente a un empleado
# ============================================================

@login_required
def asignar_expediente(request, expediente_id):
    empresa = _empresa_actual(request)
    expediente = get_object_or_404(ExpedienteCobranza, id=expediente_id, empresa=empresa)

    if request.method != "POST":
        return redirect("detalle_expediente", expediente_id=expediente.id)

    empleado_id = request.POST.get("empleado_id")

    if not empleado_id:
        expediente.asignado_a = None
        expediente.save(update_fields=["asignado_a"])
        messages.success(request, "Expediente sin asignar.")
        return redirect("detalle_expediente", expediente_id=expediente.id)

    empleado = get_object_or_404(Empleado, id=empleado_id, empresa=empresa, activo=True)

    expediente.asignado_a = empleado
    expediente.save(update_fields=["asignado_a"])

    GestionCobranza.objects.create(
        expediente=expediente, tipo_gestion="nota", resultado="otro",
        registrado_por=request.user,
        notas=f"Expediente asignado a {empleado.nombre}.",
    )

    messages.success(request, f"Expediente asignado a {empleado.nombre}.")
    return redirect("detalle_expediente", expediente_id=expediente.id)


# ============================================================
# parte 8: Resumen de Cobranza (solo portal)
# ============================================================

@login_o_portal_required
def resumen_cobranza_portal(request):
    if not getattr(request, "is_portal_acceso", False):
        messages.error(request, "Esta pantalla es exclusiva del portal de administradores y comités.")
        return redirect("dashboard_inicio")

    empresa = getattr(request, "empresa_activa_portal", None)
    if not empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("acceso_dashboard")

    hoy = timezone.now().date()
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - datetime.timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    # --- Cartera activa (en vivo) ---
    expedientes_activos = list(
        ExpedienteCobranza.objects.filter(empresa=empresa, estatus='activo').select_related('cliente')
    )
    _precomputar_saldos_expedientes(expedientes_activos, empresa)

    cartera_vencida_total = sum(e.saldo_vencido_total for e in expedientes_activos)
    total_expedientes_activos = len(expedientes_activos)

    # --- Antigüedad de cartera ---
    # NUEVO -- se usan llaves de diccionario "seguras" para Django
    # templates (sin "-" ni "+", que no son válidos en el acceso por
    # punto dentro de un template) -- rango_antiguedad en el modelo se
    # queda igual, solo se traduce aquí.
    MAPA_RANGOS = {'0-30': 'r0_30', '31-60': 'r31_60', '61-90': 'r61_90', '90+': 'r90_mas'}
    rangos_orden = ['r0_30', 'r31_60', 'r61_90', 'r90_mas']
    antiguedad = {r: {"cantidad": 0, "monto": Decimal("0")} for r in rangos_orden}
    for e in expedientes_activos:
        r = MAPA_RANGOS[e.rango_antiguedad]
        antiguedad[r]["cantidad"] += 1
        antiguedad[r]["monto"] += e.saldo_vencido_total

    # --- Pipeline por etapa ---
    por_etapa = []
    for etapa_key, etapa_label in ExpedienteCobranza.ETAPA_CHOICES:
        if etapa_key == "cerrado":
            continue
        en_esta_etapa = [e for e in expedientes_activos if e.etapa == etapa_key]
        por_etapa.append({
            "label": etapa_label,
            "cantidad": len(en_esta_etapa),
            "monto": sum(e.saldo_vencido_total for e in en_esta_etapa),
        })

    # --- Top 10 deudores ---
    top_deudores = sorted(expedientes_activos, key=lambda e: e.saldo_vencido_total, reverse=True)[:10]

    # --- Recuperado este mes vs. mes anterior (basado en monto_al_cierre) ---
    cerrados_mes_actual = ExpedienteCobranza.objects.filter(
        empresa=empresa, estatus='cerrado',
        fecha_cierre__date__gte=primer_dia_mes_actual, fecha_cierre__date__lte=hoy,
        monto_al_cierre__isnull=False,
    )
    cerrados_mes_anterior = ExpedienteCobranza.objects.filter(
        empresa=empresa, estatus='cerrado',
        fecha_cierre__date__gte=primer_dia_mes_anterior, fecha_cierre__date__lte=ultimo_dia_mes_anterior,
        monto_al_cierre__isnull=False,
    )

    recuperado_mes_actual = cerrados_mes_actual.aggregate(t=Sum('monto_al_cierre'))['t'] or Decimal("0")
    casos_resueltos_mes_actual = cerrados_mes_actual.count()
    recuperado_mes_anterior = cerrados_mes_anterior.aggregate(t=Sum('monto_al_cierre'))['t'] or Decimal("0")

    if recuperado_mes_anterior > 0:
        variacion_pct = ((recuperado_mes_actual - recuperado_mes_anterior) / recuperado_mes_anterior) * 100
    else:
        variacion_pct = None

    return render(request, "gestion_cobranza/resumen_portal.html", {
        "empresa": empresa,
        "hoy": hoy,
        "cartera_vencida_total": cartera_vencida_total,
        "total_expedientes_activos": total_expedientes_activos,
        "antiguedad": antiguedad,
        "rangos_orden": rangos_orden,
        "por_etapa": por_etapa,
        "top_deudores": top_deudores,
        "recuperado_mes_actual": recuperado_mes_actual,
        "recuperado_mes_anterior": recuperado_mes_anterior,
        "casos_resueltos_mes_actual": casos_resueltos_mes_actual,
        "variacion_pct": variacion_pct,
        "mes_actual_label": primer_dia_mes_actual.strftime("%B %Y"),
        "mes_anterior_label": primer_dia_mes_anterior.strftime("%B %Y"),
    })