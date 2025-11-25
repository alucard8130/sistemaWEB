import csv
from decimal import ROUND_HALF_UP
import locale
import os
from typing_extensions import OrderedDict
from urllib import response
from uuid import uuid4
import uuid
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db import transaction
from openai import base_url
import openpyxl
from areas import models
from core import settings
from empleados.models import Empleado
from empresas.models import Empresa
from clientes.models import Cliente
from facturacion.forms import TimbrarFacturaForm
from gastos.models import Gasto
from locales.models import LocalComercial
from areas.models import AreaComun
from facturacion.models import CobroOtrosIngresos, Factura, FacturaOtrosIngresos, Pago
from presupuestos.models import Presupuesto, PresupuestoIngreso
from principal.forms import TemaGeneralForm, VisitanteLoginForm
from principal.models import AuditoriaCambio
from proveedores.models import Proveedor
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from .models import Aviso, Evento, PerfilUsuario, TemaGeneral, VisitanteAcceso, VotacionCorreo
import json
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
import stripe
from .models import TicketMantenimiento
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import TicketMantenimiento, SeguimientoTicket
from django.contrib.auth.hashers import check_password
from django.urls import reverse
from django.conf import settings
import requests
from decimal import Decimal
from .forms import AvisoForm, CSDUploadForm, EstadoCuentaUploadForm
import base64
import io
import zipfile
from gastos.models import PagoGasto
from .serializers import FacturaSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime,date
from caja_chica.models import FondeoCajaChica, GastoCajaChica, ValeCaja
import logging
from facturacion.models import Factura, Pago
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes, parser_classes
from .models import VisitanteToken
from functools import wraps
from django.db.models import Sum
from django.db.models import Case, When, Value, CharField, Q, DecimalField, ExpressionWrapper, OuterRef, Subquery, F
from django.db.models.functions import Coalesce
from rest_framework.parsers import MultiPartParser, FormParser


# Vista de bienvenida / dashboard
@login_required
def bienvenida(request):
    empresa = None
    es_demo = False
    perfil = request.user.perfilusuario
    mostrar_wizard = perfil.mostrar_wizard

    mensaje_pago = None
    if request.GET.get("pago") == "ok":
        mensaje_pago = "¡Tu suscripción se ha activado correctamente! Puedes empezar a usar el sistema."

    if not request.user.is_superuser:
        empresa = request.user.perfilusuario.empresa
        eventos = Evento.objects.filter(empresa=empresa).order_by("fecha")
        es_demo = request.user.perfilusuario.tipo_usuario == "demo"
    else:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                eventos = Evento.objects.filter(empresa=empresa).order_by("fecha")
            except Empresa.DoesNotExist:
                empresa = None
                eventos = Evento.objects.all().order_by("fecha")
        else:
            eventos = Evento.objects.all().order_by("fecha")
    return render(
        request,
        "bienvenida.html",
        {
            "empresa": empresa,
            "eventos": eventos,
            "es_demo": es_demo,
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
            "mostrar_wizard": mostrar_wizard,
            "mensaje_pago": mensaje_pago,
        },
    )


# Configuración del sistema
@staff_member_required
@login_required
def reiniciar_sistema(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Orden: pagos > facturas > locales/areas > clientes > empresas etc...

                Factura.objects.all().delete()
                LocalComercial.objects.all().delete()
                AreaComun.objects.all().delete()
                Cliente.objects.all().delete()
                # Empresa.objects.all().delete()
                Proveedor.objects.all().delete()
                Empleado.objects.all().delete()
                Gasto.objects.all().delete()
                Presupuesto.objects.all().delete()
                AuditoriaCambio.objects.all().delete()
                Evento.objects.all().delete()
                Pago.objects.all().delete()

            messages.success(request, "¡El sistema fue reiniciado exitosamente!")
        except Exception as e:
            messages.error(request, f"Error al reiniciar: {e}")
        return redirect("bienvenida")
    return render(request, "reiniciar_sistema.html")


@staff_member_required
def respaldo_empresa_excel(request):
    # Si no hay empresa seleccionada, muestra el formulario
    if request.method == "GET" and "empresa_id" not in request.GET:
        empresas = Empresa.objects.all()
        return render(request, "respaldo_empresas.html", {"empresas": empresas})

    empresa_id = request.GET.get("empresa_id")
    try:
        empresa = Empresa.objects.get(pk=empresa_id)
    except Empresa.DoesNotExist:
        return render(
            request,
            "respaldo_empresas.html",
            {"empresas": Empresa.objects.all(), "error": "Empresa no encontrada."},
        )

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Borra hoja por defecto

    # CLIENTES
    ws = wb.create_sheet("Clientes")
    ws.append(["id", "nombre", "rfc", "telefono", "email", "activo"])
    for c in Cliente.objects.filter(empresa=empresa):
        ws.append([c.id, c.nombre, c.rfc, c.telefono, c.email, c.activo])

    # LOCALES
    ws = wb.create_sheet("Locales")
    ws.append(
        [
            "id",
            "numero",
            "cliente",
            "ubicacion",
            "superficie_m2",
            "cuota",
            "status",
            "activo",
            "observaciones",
        ]
    )
    for l in LocalComercial.objects.filter(empresa=empresa):
        ws.append(
            [
                l.id,
                l.numero,
                l.cliente.nombre if l.cliente else "",
                l.ubicacion,
                l.superficie_m2,
                l.cuota,
                l.status,
                l.activo,
                l.observaciones,
            ]
        )

    # ÁREAS COMUNES
    ws = wb.create_sheet("Áreas Comunes")
    ws.append(
        [
            "cliente",
            "numero",
            "cuota",
            "ubicacion",
            "superficie_m2",
            "status",
            "fecha_inicial",
            "fecha_fin",
            "activo",
            "observaciones",
        ]
    )
    for a in AreaComun.objects.filter(empresa=empresa):
        ws.append(
            [
                a.cliente.nombre if a.cliente else "",
                a.numero,
                a.cuota,
                a.ubicacion,
                a.superficie_m2,
                a.status,
                str(a.fecha_inicial) if a.fecha_inicial else "",
                str(a.fecha_fin) if a.fecha_fin else "",
                a.activo,
                a.observaciones,
            ]
        )

    # FACTURAS
    ws = wb.create_sheet("Facturas")
    ws.append(
        [
            "folio",
            "cliente",
            "local",
            "area_comun",
            "monto",
            "fecha_emision",
            "fecha_vencimiento",
            "estatus",
        ]
    )
    for f in Factura.objects.filter(empresa=empresa):
        ws.append(
            [
                f.folio,
                f.cliente.nombre if f.cliente else "",
                f.local.numero if f.local else "",
                f.area_comun.numero if f.area_comun else "",
                float(f.monto),
                str(f.fecha_emision),
                str(f.fecha_vencimiento),
                f.estatus,
            ]
        )

    # PAGOS
    ws = wb.create_sheet("Pagos")
    ws.append(["id", "factura", "fecha_pago", "monto", "registrado_por"])
    for p in Pago.objects.filter(factura__empresa=empresa):
        ws.append(
            [
                p.id,
                p.factura.folio if p.factura else "",
                str(p.fecha_pago),
                float(p.monto),
                p.registrado_por.get_full_name() if p.registrado_por else "",
            ]
        )

    # GASTOS
    ws = wb.create_sheet("Gastos")
    ws.append(
        ["id", "proveedor", "empleado", "descripcion", "monto", "tipo_gasto", "fecha"]
    )
    for g in Gasto.objects.filter(empresa=empresa):
        ws.append(
            [
                g.id,
                str(g.proveedor) if g.proveedor else "",
                str(g.empleado) if g.empleado else "",
                g.descripcion,
                float(g.monto),
                str(g.tipo_gasto) if g.tipo_gasto else "",
                str(g.fecha),
            ]
        )

    # PAGOS GASTOS
    ws = wb.create_sheet("Pagos Gastos")
    ws.append(["id", "referencia", "fecha_pago", "monto", "registrado_por"])
    for g in Gasto.objects.filter(empresa=empresa):
        for pago in g.pagos.all():
            ws.append(
                [
                    pago.id,
                    pago.referencia,
                    str(pago.fecha_pago),
                    float(pago.monto),
                    pago.registrado_por.get_full_name() if pago.registrado_por else "",
                ]
            )

    # PRESUPUESTOS
    ws = wb.create_sheet("Presupuestos")
    ws.append(
        ["id", "empresa", "grupo", "subgrupo", "tipo_gasto", "anio", "mes", "monto"]
    )
    for p in Presupuesto.objects.filter(empresa=empresa):
        ws.append(
            [
                p.id,
                p.empresa.nombre if p.empresa else "",
                str(p.grupo) if p.grupo else "",
                str(p.subgrupo) if p.subgrupo else "",
                str(p.tipo_gasto) if p.tipo_gasto else "",
                p.anio,
                p.mes,
                float(p.monto),
            ]
        )
        # PRESUPUESTOS INGRESOS
    ws = wb.create_sheet("Presupuestos Ingresos")
    ws.append(["id", "empresa", "tipo_ingreso", "anio", "mes", "monto"])
    for p in PresupuestoIngreso.objects.filter(empresa=empresa):
        ws.append(
            [
                p.id,
                p.empresa.nombre if p.empresa else "",
                str(p.tipo_ingreso) if hasattr(p, "tipo_ingreso") else "",
                p.anio,
                p.mes,
                float(p.monto),
            ]
        )

    # EMPLEADOS
    ws = wb.create_sheet("Empleados")
    ws.append(["id", "nombre", "email", "telefono", "puesto", "activo"])
    for e in Empleado.objects.filter(empresa=empresa):
        ws.append([e.id, e.nombre, e.email, e.telefono, e.puesto, e.activo])

    # PROVEEDORES
    ws = wb.create_sheet("Proveedores")
    ws.append(["id", "nombre", "rfc", "telefono", "email", "activo"])
    for p in Proveedor.objects.filter(empresa=empresa):
        ws.append([p.id, str(p.nombre), p.rfc, p.telefono, p.email, p.activo])

    # OTROS INGRESOS
    ws = wb.create_sheet("Otros Ingresos")
    ws.append(
        [
            "id",
            "folio",
            "cliente",
            "tipo_ingreso",
            "monto",
            "saldo",
            "fecha_emision",
            "fecha_vencimiento",
            "estatus",
            "observaciones",
        ]
    )
    for f in FacturaOtrosIngresos.objects.filter(empresa=empresa):
        ws.append(
            [
                f.id,
                f.folio,
                f.cliente.nombre if f.cliente else "",
                str(f.tipo_ingreso) if hasattr(f, "tipo_ingreso") else "",
                float(f.monto),
                float(f.saldo),
                str(f.fecha_emision),
                str(f.fecha_vencimiento) if f.fecha_vencimiento else "",
                f.estatus,
                f.observaciones or "",
            ]
        )

    # PAGOS OTROS INGRESOS
    ws = wb.create_sheet("Pagos Otros Ingresos")
    ws.append(["id", "factura", "fecha_pago", "monto", "registrado_por"])
    for p in CobroOtrosIngresos.objects.filter(factura__empresa=empresa):
        ws.append(
            [
                p.id,
                p.factura.folio if p.factura else "",
                str(p.fecha_pago),
                float(p.monto),
                p.registrado_por.get_full_name() if p.registrado_por else "",
            ]
        )

    # Responde el archivo Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f"attachment; filename=respaldo_empresa_{empresa.nombre}.xlsx"
    )
    wb.save(response)
    return response


@staff_member_required
def reporte_auditoria(request):
    modelo = request.GET.get("modelo")
    queryset = AuditoriaCambio.objects.all().order_by("-fecha_cambio")
    if modelo in ["local", "area", "factura"]:
        queryset = queryset.filter(modelo=modelo)
    return render(
        request, "auditoria/reporte.html", {"auditorias": queryset, "modelo": modelo}
    )


@csrf_exempt
@login_required
def crear_evento(request):
    if request.method == "POST":
        empresa = request.user.perfilusuario.empresa
        data = json.loads(request.body)
        evento = Evento.objects.create(
            empresa=empresa,
            titulo=data.get("titulo"),
            fecha=data.get("fecha"),
            descripcion=data.get("descripcion"),
            creado_por=request.user,
        )

        evento.save()
        return JsonResponse({"ok": True, "id": evento.id})
    return JsonResponse({"ok": False}, status=400)


@csrf_exempt
@login_required
def eliminar_evento(request, evento_id):
    if request.method == "POST":
        try:
            evento = Evento.objects.get(
                id=evento_id, empresa=request.user.perfilusuario.empresa
            )
            evento.delete()
            return JsonResponse({"ok": True})
        except Evento.DoesNotExist:
            return JsonResponse({"ok": False, "error": "No encontrado"}, status=404)
    return JsonResponse({"ok": False}, status=400)


@csrf_exempt
@login_required
def enviar_correo_evento(request, evento_id):
    if request.method == "POST":
        correo_destino = request.POST.get("correo")
        archivos = request.FILES.getlist("archivos")
        try:
            evento = Evento.objects.get(
                id=evento_id, empresa=request.user.perfilusuario.empresa
            )
            if correo_destino:
                cuerpo_html = render_to_string(
                    "correo_evento.html", {"evento": evento, "empresa": evento.empresa}
                )
                email = EmailMessage(
                    subject=f"Nuevo evento: {evento.titulo}",
                    body=cuerpo_html,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[correo_destino],
                )
                email.content_subtype = "html"
                for archivo in archivos:
                    email.attach(archivo.name, archivo.read(), archivo.content_type)
                email.send(fail_silently=False)
                evento.enviado_correo = True
                evento.save()
                return JsonResponse({"ok": True})
            else:
                return JsonResponse(
                    {"ok": False, "error": "Correo no proporcionado"}, status=400
                )
        except Evento.DoesNotExist:
            return JsonResponse(
                {"ok": False, "error": "Evento no encontrado"}, status=404
            )
    return JsonResponse({"ok": False}, status=400)


def registro_usuario(request):
    mensaje = ""
    if request.method == "POST":
        nombre = request.POST["nombre"]
        username = request.POST["username"]
        password = request.POST["password"]
        email = request.POST["email"]
        # telefono = request.POST['telefono']

        if User.objects.filter(username=username).exists():
            mensaje = "El nombre de usuario ya está en uso. Por favor elige otro."
        else:
            user = User.objects.create_user(
                username=username, password=password, email=email, first_name=nombre
            )
            empresa = Empresa.objects.create(
                nombre="EMPRESA DEMO AC", rfc=f"DEMO{uuid4().hex[:8].upper()}"
            )
            # PerfilUsuario.objects.create(
            #     usuario=user, empresa=empresa, tipo_usuario="demo"
            # )
            # Asigna la empresa y tipo_usuario al perfil creado por la señal
            perfil = user.perfilusuario
            perfil.empresa = empresa
            if not user.is_superuser:
                perfil.tipo_usuario = "demo"
            perfil.save()
            return redirect("login")
    return render(request, "registro.html", {"mensaje": mensaje})


@staff_member_required
@login_required
def usuarios_demo(request):
    usuarios = User.objects.filter(perfilusuario__tipo_usuario="demo")
    usuarios_info = []
    for user in usuarios:
        dias = (date.today() - user.date_joined.date()).days
        usuarios_info.append(
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "email": user.email,
                "is_active": user.is_active,
                "dias_demo": dias,
            }
        )
    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion == "inactivar":
            ids = request.POST.getlist("inactivar")
            User.objects.filter(id__in=ids).update(is_active=False)
        elif accion == "reactivar":
            ids = request.POST.getlist("reactivar")
            User.objects.filter(id__in=ids).update(is_active=True)
        elif accion == "reactivar_todos":
            User.objects.filter(perfilusuario__tipo_usuario="demo").update(
                is_active=True
            )
        return redirect("usuarios_demo")
    return render(request, "usuarios_demo.html", {"usuarios": usuarios_info})


# Webhook de Stripe pago sistema de suscripciones GESAC
@csrf_exempt
def stripe_webhook(request):
    import stripe
    from django.http import HttpResponse
    from django.conf import settings
    from .models import PerfilUsuario
    from django.contrib.auth.models import User

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        print("Error Stripe:", e)
        return HttpResponse(status=400)

    # Activación inicial de suscripción
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        email = session.get("customer_details", {}).get("email")
        if customer_id:
            try:
                perfil = PerfilUsuario.objects.get(stripe_customer_id=customer_id)
                user = perfil.usuario
                user.is_active = True
                perfil.tipo_usuario = "pago"
                # Solo mostrar el wizard si nunca ha tenido suscripción
                if not perfil.stripe_subscription_id:
                    perfil.mostrar_wizard = True
                if subscription_id:
                    perfil.stripe_subscription_id = subscription_id
                perfil.save()
                user.save()
            except PerfilUsuario.DoesNotExist:
                if email:
                    try:
                        user = User.objects.get(email=email)
                        perfil = PerfilUsuario.objects.get(usuario=user)
                        perfil.stripe_customer_id = customer_id
                        perfil.tipo_usuario = "pago"
                        # Solo mostrar el wizard si nunca ha tenido suscripción
                        if not perfil.stripe_subscription_id:
                            perfil.mostrar_wizard = True
                        if subscription_id:
                            perfil.stripe_subscription_id = subscription_id
                        perfil.save()
                        user.is_active = True
                        user.save()
                    except (User.DoesNotExist, PerfilUsuario.DoesNotExist):
                        print("No se pudo encontrar el usuario asociado al pago.")

    # Renovación automática de suscripción
    if event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        if customer_id:
            try:
                perfil = PerfilUsuario.objects.get(stripe_customer_id=customer_id)
                perfil.tipo_usuario = "pago"
                perfil.save()
                print("Renovación automática: acceso renovado.")
            except PerfilUsuario.DoesNotExist:
                print("No se encontró perfil para renovar acceso.")

    return HttpResponse(status=200)


@login_required
def crear_sesion_pago(request):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                # "price": "price_1RqexnPYnlfwKZQHILP9tgW5",
                "price": "price_1RxsU7PYnlfwKZQH4u5DJ7aH",
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url=request.build_absolute_uri("/bienvenida/?pago=ok"),
        cancel_url=request.build_absolute_uri("/"),
        client_reference_id=str(request.user.id),  # Para identificar al usuario
        customer_email=request.user.email,
    )
    return JsonResponse({"id": session.id})


@login_required
def cancelar_suscripcion(request):
    perfil = request.user.perfilusuario
    subscription_id = perfil.stripe_subscription_id
    if subscription_id:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            stripe.Subscription.delete(subscription_id)
            perfil.tipo_usuario = "demo"  # O el estado que corresponda
            perfil.save()
            return JsonResponse({"status": "cancelada"})
        except Exception as e:
            return JsonResponse({"status": "error", "detail": str(e)}, status=400)
    return JsonResponse({"status": "no encontrada"}, status=404)


@require_POST
@login_required
def guardar_datos_empresa(request):
    perfil = request.user.perfilusuario
    empresa = perfil.empresa
    nuevo_rfc = request.POST.get("rfc_empresa", "").strip()

    if Empresa.objects.filter(rfc=nuevo_rfc).exclude(id=empresa.id).exists():
        messages.error(request, "El RFC ingresado ya está registrado en otra empresa.")
        return redirect("bienvenida")

    empresa.nombre = request.POST.get("nombre_empresa", "")
    empresa.rfc = nuevo_rfc
    empresa.direccion = request.POST.get("direccion_empresa", "")
    empresa.email = request.POST.get("email_empresa", "")
    empresa.telefono = request.POST.get("telefono_empresa", "")
    empresa.cuenta_bancaria = request.POST.get("cuenta_bancaria", "")
    empresa.numero_cuenta = request.POST.get("numero_cuenta", "")
    try:
        empresa.saldo_inicial = float(request.POST.get("saldo_inicial", 0.00))
    except ValueError:
        empresa.saldo_inicial = 0.00
    empresa.save()
    perfil.mostrar_wizard = False
    perfil.save()
    messages.success(request, "¡Datos de empresa actualizados correctamente!")
    return redirect("bienvenida")


# MODULO DE TICKETS DE MANTENIMIENTO-->
@login_required
def crear_ticket(request):
    empresa = request.user.perfilusuario.empresa
    empleados = Empleado.objects.filter(empresa=empresa, activo=True)
    if request.method == "POST":
        titulo = request.POST["titulo"]
        descripcion = request.POST["descripcion"]
        empleado_id = request.POST["empleado_asignado"]
        empleado = Empleado.objects.get(id=empleado_id)
        ticket = TicketMantenimiento.objects.create(
            titulo=titulo, descripcion=descripcion, empleado_asignado=empleado
        )
        # Enviar correo si el empleado tiene email
        if empleado.email:
            # Preparar email con adjuntos (si hay)
            asunto = "Nuevo reporte de mantenimiento asignado"
            cuerpo = f"Empresa: {empresa.nombre}\nSe te ha asignado el reporte: {titulo}\n\nDescripción: {descripcion}"
            email = EmailMessage(
                subject=asunto,
                body=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[empleado.email],
            )
            # Adjuntar imágenes si fueron subidas
            archivos = request.FILES.getlist("imagenes")
            MAX_SIZE = 5 * 1024 * 1024  # 5MB por archivo
            skipped = []
            attached_count = 0
            for f in archivos:
                try:
                    content_type = getattr(f, "content_type", "") or ""
                    # validar tipo y tamaño
                    if not content_type.startswith("image/"):
                        skipped.append(f"{f.name} (no es imagen)")
                        continue
                    if f.size > MAX_SIZE:
                        skipped.append(f"{f.name} (>{int(MAX_SIZE/1024/1024)}MB)")
                        continue
                    # adjuntar
                    email.attach(f.name, f.read(), content_type)
                    attached_count += 1
                except Exception:
                    skipped.append(f"{f.name} (error al adjuntar)")
                    continue
            try:
                email.send(fail_silently=True)
            except Exception:
                pass

            # Informar al usuario sobre adjuntos omitidos/adjuntados
            if attached_count:
                messages.info(
                    request, f"Se adjuntaron {attached_count} imagen(es) al correo."
                )
            if skipped:
                messages.warning(
                    request,
                    "Se omitieron archivos al enviar el correo: "
                    + ", ".join(skipped[:20])
                    + (f", ...(+{len(skipped)-20})" if len(skipped) > 20 else ""),
                )

        # # Enviar notificación por WhatsApp si el empleado tiene teléfono
        # #PENDIENTE CONFIGURAR CLOUD API DE WHATSAPP (META)
        # if empleado.telefono:
        #     # Normalizar número (quitar espacios, paréntesis, guiones)
        #     phone_raw = str(empleado.telefono)
        #     phone_digits = "".join(ch for ch in phone_raw if ch.isdigit())
        #     # Quitar prefijo internacional 00 si existe
        #     if phone_digits.startswith("00"):
        #         phone_digits = phone_digits[2:]
        #     # Si aún no tiene código de país intenta no modificar; WhatsApp Cloud API requiere formato internacional
        #     whatsapp_phone = phone_digits

        #     # Intento con WhatsApp Cloud API (Meta) si están configuradas las vars de entorno
        #     whatsapp_phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")  # e.g. "109876543210" (your phone number id)
        #     whatsapp_token = os.getenv("WHATSAPP_TOKEN")  # bearer token (long-lived)

        #     msg_text = f"Se te ha asignado el ticket: {titulo}\nDescripción: {descripcion}"

        #     if whatsapp_phone_id and whatsapp_token:
        #         headers = {"Authorization": f"Bearer {whatsapp_token}"}
        #         base_url = f"https://graph.facebook.com/v15.0/{whatsapp_phone_id}"

        #         # 1) Enviar texto
        #         try:
        #             payload = {
        #                 "messaging_product": "whatsapp",
        #                 "to": whatsapp_phone,
        #                 "type": "text",
        #                 "text": {"body": msg_text}
        #             }
        #             requests.post(f"{base_url}/messages", json=payload, headers=headers, timeout=10)
        #         except Exception:
        #             # no interrumpe el flujo si falla WhatsApp
        #             pass

        #         # 2) Si hay imágenes subidas, subir y enviar cada una como media
        #         archivos = request.FILES.getlist("imagenes")
        #         MAX_SIZE = 5 * 1024 * 1024  # 5MB por archivo
        #         for f in archivos:
        #             try:
        #                 ct = getattr(f, "content_type", "") or ""
        #                 if not ct.startswith("image/"):
        #                     continue
        #                 if f.size > MAX_SIZE:
        #                     continue
        #                 # Subir media -> devuelve id
        #                 files = {"file": (f.name, f.read(), ct)}
        #                 params = {"messaging_product": "whatsapp"}
        #                 r = requests.post(f"{base_url}/media", files=files, params=params, headers=headers, timeout=30)
        #                 media_resp = r.json() if r.ok else {}
        #                 media_id = media_resp.get("id")
        #                 if media_id:
        #                     img_payload = {
        #                         "messaging_product": "whatsapp",
        #                         "to": whatsapp_phone,
        #                         "type": "image",
        #                         "image": {"id": media_id, "caption": titulo}
        #                     }
        #                     requests.post(f"{base_url}/messages", json=img_payload, headers=headers, timeout=10)
        #             except Exception:
        #                 continue
        #     else:
        #         # Fallback mínimo: construir URL wa.me para abrir en cliente (no puedo enviar desde servidor sin API)
        #         # Se guarda en logs/messages para que el operador lo use
        #         wa_link = f"https://wa.me/{whatsapp_phone}?text={requests.utils.requote_uri(msg_text)}"
        #         # opcional: registrar en mensajes de Django para que el admin lo vea
        #         messages.info(request, f"No está configurada la API de WhatsApp. Abre este enlace para notificar manualmente: {wa_link}")

        return redirect("lista_tickets")
    return render(request, "mantenimiento/crear_ticket.html", {"empleados": empleados})


@login_required
def actualizar_ticket(request, ticket_id):
    ticket = TicketMantenimiento.objects.get(id=ticket_id)
    if request.method == "POST":
        ticket.estado = request.POST["estado"]
        ticket.solucion = request.POST.get("solucion", "")
        if ticket.estado == "resuelto":
            ticket.fecha_solucion = timezone.now()
        ticket.save()
        return redirect("detalle_ticket", ticket_id=ticket.id)
    return render(request, "mantenimiento/actualizar_ticket.html", {"ticket": ticket})


@login_required
def agregar_seguimiento(request, ticket_id):
    ticket = get_object_or_404(TicketMantenimiento, id=ticket_id)
    if request.method == "POST":
        comentario = request.POST["comentario"]
        SeguimientoTicket.objects.create(
            ticket=ticket, usuario=request.user, comentario=comentario
        )
    return redirect("detalle_ticket", ticket_id=ticket.id)


@login_required
def detalle_ticket(request, ticket_id):
    ticket = TicketMantenimiento.objects.get(id=ticket_id)
    seguimientos = ticket.seguimientos.order_by("-fecha")
    return render(
        request,
        "mantenimiento/detalle_ticket.html",
        {"ticket": ticket, "seguimientos": seguimientos},
    )


@login_required
def tickets_asignados(request):
    empresa = request.user.perfilusuario.empresa
    empleados = Empleado.objects.filter(empresa=empresa, activo=True)
    empleado_id = request.GET.get("empleado_id")
    tickets = []
    empleado_seleccionado = None
    if empleado_id:
        empleado_seleccionado = Empleado.objects.filter(
            id=empleado_id, empresa=empresa
        ).first()
        tickets = TicketMantenimiento.objects.filter(
            empleado_asignado=empleado_seleccionado
        )
    return render(
        request,
        "mantenimiento/tickets_asignados.html",
        {
            "empleados": empleados,
            "tickets": tickets,
            "empleado_seleccionado": empleado_seleccionado,
        },
    )


@login_required
def lista_tickets(request):
    if request.user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            tickets = TicketMantenimiento.objects.filter(
                empleado_asignado__empresa_id=empresa_id
            ).order_by("-fecha_creacion")
        else:
            tickets = TicketMantenimiento.objects.all().order_by("-fecha_creacion")
    else:
        empresa = request.user.perfilusuario.empresa
        tickets = TicketMantenimiento.objects.filter(
            empleado_asignado__empresa=empresa
        ).order_by("-fecha_creacion")
    return render(request, "mantenimiento/lista_tickets.html", {"tickets": tickets})


@login_required
def seleccionar_empresa(request):
    if not request.user.is_superuser:
        return redirect("bienvenida")  # O la vista normal

    if request.method == "POST":
        empresa_id = request.POST.get("empresa")
        if empresa_id:
            request.session["empresa_id"] = empresa_id
            return redirect("bienvenida")  # O la vista principal
    empresas = Empresa.objects.all()
    return render(request, "seleccionar_empresa.html", {"empresas": empresas})


# modulo visitantes consulta adeudos y pagos de facturas-->
def visitante_login(request):
    if request.method == "POST":
        form = VisitanteLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            try:
                visitante = VisitanteAcceso.objects.get(username=username)
                if check_password(password, visitante.password):
                    request.session["visitante_id"] = visitante.id
                    return redirect("visitante_consulta_facturas")
                else:
                    messages.error(request, "Contraseña incorrecta.")
            except VisitanteAcceso.DoesNotExist:
                messages.error(request, "Usuario no encontrado.")
    else:
        form = VisitanteLoginForm()
    return render(request, "visitantes/login.html", {"form": form})


def visitante_consulta_facturas(request):
    visitante_id = request.session.get("visitante_id")
    if not visitante_id:
        return redirect("visitante_login")
    visitante = VisitanteAcceso.objects.get(id=visitante_id)

    # Filtros
    local_id = request.GET.get("local_id")
    area_id = request.GET.get("area_id")
    pagook = request.GET.get("pagook")
    factura_id = request.GET.get("factura_id")
    anio = request.GET.get("anio")

    locales = visitante.locales.all()
    areas = visitante.areas.all()

    facturas = Factura.objects.none()
    if local_id:
        facturas = Factura.objects.filter(local_id=local_id, local__in=locales)
    elif area_id:
        facturas = Factura.objects.filter(area_comun_id=area_id, area_comun__in=areas)
    else:
        facturas = Factura.objects.filter(
            Q(local__in=locales) | Q(area_comun__in=areas)
        )

    # Obtén los años únicos de las facturas
    anios_unicos = (
        facturas.order_by().values_list("fecha_vencimiento__year", flat=True).distinct()
    )
    anios_unicos = sorted(set(filter(None, anios_unicos)), reverse=True)

    # Filtro por año
    if anio and anio.isdigit():
        facturas = facturas.filter(fecha_vencimiento__year=int(anio))

    # Calcula total pendiente y total cobrado
    total_pendiente = sum(
        f.saldo_pendiente for f in facturas if f.estatus == "pendiente"
    )
    total_cobrado = sum(f.monto for f in facturas if f.estatus == "cobrada")

    mensaje_pago = None
    if pagook and factura_id:
        try:
            factura_pagada = Factura.objects.get(id=factura_id)
            mensaje_pago = f"¡Pago de la factura {factura_pagada.folio}: realizado correctamente! En breve se reflejará en el sistema."
        except Factura.DoesNotExist:
            mensaje_pago = (
                "¡Pago realizado correctamente! En breve se reflejará en el sistema."
            )

    factura_pendiente_mas_antigua = (
        facturas.filter(estatus="pendiente").order_by("fecha_vencimiento").first()
    )
    factura_pendiente_id = (
        factura_pendiente_mas_antigua.id if factura_pendiente_mas_antigua else None
    )

    return render(
        request,
        "facturacion/consulta_facturas.html",
        {
            "facturas": facturas,
            "visitante": visitante,
            "locales": locales,
            "areas": areas,
            "local_id": local_id,
            "area_id": area_id,
            "total_pendiente": total_pendiente,
            "total_cobrado": total_cobrado,
            "es_visitante": True,
            "mensaje_pago": mensaje_pago,
            "anio": anio,
            "anios_unicos": anios_unicos,
            "factura_pendiente_id": factura_pendiente_id,
        },
    )


def visitante_logout(request):
    request.session.flush()
    return redirect("visitante_login")


def visitante_factura_detalle(request, factura_id):
    visitante_id = request.session.get("visitante_id")
    if not visitante_id:
        return redirect("visitante_login")
    visitante = VisitanteAcceso.objects.get(id=visitante_id)
    factura = get_object_or_404(Factura, id=factura_id)
    # Verifica que la factura pertenezca a los locales/áreas del visitante
    if (
        factura.local not in visitante.locales.all()
        and factura.area_comun not in visitante.areas.all()
    ):
        return redirect("visitante_consulta_facturas")
    cobros = factura.pagos.all()
    return render(
        request,
        "facturacion/facturas_detalle.html",
        {"factura": factura, "cobros": cobros, "es_visitante": True},
    )


# Pago con Stripe para visitantes multiempresas
def stripe_checkout_visitante(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    empresa = factura.empresa

    # Verifica que la empresa tenga las claves de Stripe configuradas
    if not (
        empresa.stripe_secret_key
        and empresa.stripe_public_key
        and empresa.stripe_webhook_secret
    ):
        messages.error(
            request,
            " PAGO EN LINEA no esta configurado. Contacta al administrador del sistema.",
        )
        return redirect("visitante_consulta_facturas")
    elif not empresa.es_plus:
        messages.error(
            request,
            " PAGO EN LINEA solo está disponible en la versión PLUS del sistema.Contacta al administrador del sistema.",
        )
        return redirect(
            "visitante_consulta_facturas"
        )  # O la vista/lista que corresponda

    stripe.api_key = empresa.stripe_secret_key  # <-- Usa la clave secreta de la empresa

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "mxn",
                    "product_data": {
                        "name": f"Pago factura {factura.folio}",
                    },
                    "unit_amount": int(factura.saldo_pendiente * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        # success_url=request.build_absolute_uri('/visitante/consulta/?pagook=1'),
        success_url=request.build_absolute_uri(
            f"/visitante/consulta/?pagook=1&factura_id={factura.id}"
        ),
        cancel_url=request.build_absolute_uri("/visitante/consulta/?pagocancel=1"),
        metadata={"factura_id": factura.id},
    )
    return redirect(session.url)


@csrf_exempt
def stripe_webhook_visitante(request):
    logger = logging.getLogger("django")
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    # 1. Carga el evento para saber el tipo
    try:
        event_data = json.loads(payload)
        event_type = event_data.get("type")
    except Exception as e:
        logger.error(f"Error leyendo el evento Stripe: {e}")
        return HttpResponse(status=400)

    # 2. Obtén el objeto y la metadata
    session = event_data.get("data", {}).get("object", {})
    metadata = session.get("metadata", {})

    # 3. Obtén el endpoint_secret (por empresa si aplica, o de settings)
    factura_id = metadata.get("factura_id")
    endpoint_secret = getattr(
        settings, "STRIPE_ENDPOINT_SECRET", None
    )  # Valor por defecto
    if factura_id:
        try:
            factura = Factura.objects.select_related("empresa").get(id=int(factura_id))
            empresa = factura.empresa
            endpoint_secret = getattr(empresa, "stripe_webhook_secret", endpoint_secret)
        except Exception as e:
            logger.error(f"Error extrayendo factura/empresa: {e}")
            return HttpResponse(status=400)

    # 4. Valida la firma del webhook
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return HttpResponse(status=400)

    # 5. Procesa eventos relevantes
    event_type = event["type"]
    obj = event["data"]["object"]
    metadata = obj.get("metadata", {})
    factura_id = metadata.get("factura_id")

    if not factura_id:
        logger.error("No se encontró factura_id en metadata.")
        return HttpResponse(status=400)

    try:
        factura = Factura.objects.get(id=int(factura_id))
        if event_type == "checkout.session.completed":
            monto_pagado = obj.get("amount_total", 0) / 100.0
            observaciones = f"ID transacción: {obj.get('payment_intent')}"
        elif event_type == "payment_intent.succeeded":
            monto_pagado = obj.get("amount", 0) / 100.0
            observaciones = f"ID transacción: {obj.get('id')}"
        else:
            logger.info(f"Ignorando evento Stripe tipo: {event_type}")
            return JsonResponse({"status": "ignored"})

        # Registra el pago y actualiza el estado
        Pago.objects.create(
            factura=factura,
            monto=monto_pagado,
            forma_pago="stripe",
            fecha_pago=timezone.now(),
            registrado_por=None,
            observaciones=observaciones,
        )
        factura.actualizar_estatus()
        factura.save()
    except Factura.DoesNotExist:
        logger.error(f"Factura no encontrada: {factura_id}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error actualizando factura: {e}")
        return HttpResponse(status=400)

    return JsonResponse({"status": "ok"})


# Módulo de votaciones por correo electrónico
def enviar_votacion(tema, lista_correos, request):
    empresa = None
    if hasattr(request.user, "perfilusuario"):
        empresa = request.user.perfilusuario.empresa
    else:
        empresa = None

    nombre_empresa = empresa.nombre if empresa else "Tu empresa"

    for correo in lista_correos:
        token = uuid4().hex
        votacion = VotacionCorreo.objects.create(tema=tema, email=correo, token=token)
        url_si = request.build_absolute_uri(
            reverse("votar_tema_correo", args=[token, "si"])
        )
        url_no = request.build_absolute_uri(
            reverse("votar_tema_correo", args=[token, "no"])
        )
        url_abstencion = request.build_absolute_uri(
            reverse("votar_tema_correo", args=[token, "abstencion"])
        )
        asunto = f"Votación: {tema.titulo} - {nombre_empresa}"
        mensaje = (
            f"Buen día,<br><br>"
            f"Estimado miembro del comité, te invitamos a participar en la siguiente votación:<br><br>"
            f"<strong>{tema.titulo}</strong><br>"
            f"{tema.descripcion}<br><br>"
            f"¿Estás de acuerdo?<br><br><br>"
            f"<a href='{url_si}' style='padding:10px 20px; background:#4caf50; color:white; text-decoration:none;'>Sí</a> "
            f"<a href='{url_no}' style='padding:10px 20px; background:#f44336; color:white; text-decoration:none;'>No</a><br><br>"
            f"<a href='{url_abstencion}' style='padding:10px 20px; background:#ffc107; color:black; text-decoration:none;'>Abstención</a><br><br>"
            f"Gracias por tu participación.<br>"
        )
        send_mail(
            subject=asunto,
            message="Te invitamos a votar. Si no ves los botones, copia y pega los enlaces en tu navegador:\nSí: {0}\nNo: {1}".format(
                url_si, url_no
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[correo],
            html_message=mensaje,
        )


def votar_tema_correo(request, token, respuesta):
    votacion = get_object_or_404(VotacionCorreo, token=token)
    if votacion.voto is not None:
        return HttpResponse("Ya has votado.")
    if respuesta not in ["si", "no", "abstencion"]:
        return HttpResponse("Respuesta inválida.")
    votacion.voto = respuesta
    votacion.fecha_voto = timezone.now()
    votacion.save()
    return HttpResponse("¡Gracias por tu voto!")


def resultados_votacion(request, tema_id):
    empresa = request.user.perfilusuario.empresa
    tema = get_object_or_404(TemaGeneral, id=tema_id, empresa=empresa)
    votos = VotacionCorreo.objects.filter(tema=tema)
    total = votos.count()
    si = votos.filter(voto="si").count()
    no = votos.filter(voto="no").count()
    abstencion = votos.filter(voto="abstencion").count()
    pendientes = votos.filter(voto__isnull=True).count()
    return render(
        request,
        "votaciones/resultados_votacion.html",
        {
            "tema": tema,
            "total": total,
            "si": si,
            "no": no,
            "abstencion": abstencion,
            "pendientes": pendientes,
            "votos": votos,
        },
    )


@login_required
def lista_temas(request):
    empresa = request.user.perfilusuario.empresa
    temas = TemaGeneral.objects.filter(empresa=empresa).order_by("-fecha_creacion")
    return render(request, "votaciones/lista_temas.html", {"temas": temas})


@login_required
def crear_tema_y_enviar(request):
    empresa = request.user.perfilusuario.empresa
    tema_id = request.GET.get("tema_id")
    tema = None
    if tema_id:
        tema = get_object_or_404(TemaGeneral, id=tema_id, empresa=empresa)
    if request.method == "POST":
        if tema:
            form = TemaGeneralForm(request.POST, instance=tema)
        else:
            form = TemaGeneralForm(request.POST)
        if form.is_valid():
            tema = form.save(commit=False)
            tema.creado_por = request.user
            tema.empresa = empresa
            tema.save()
            # Procesa los correos
            lista_correos = [
                c.strip() for c in form.cleaned_data["correos"].split(",") if c.strip()
            ]
            enviar_votacion(tema, lista_correos, request)
            messages.success(request, "Asunto creado y correos enviados.")
            return redirect("lista_temas")
    else:
        if tema:
            # Precarga los correos anteriores si existen votaciones previas
            correos_previos = ", ".join(
                VotacionCorreo.objects.filter(tema=tema).values_list("email", flat=True)
            )
            form = TemaGeneralForm(instance=tema, initial={"correos": correos_previos})
        else:
            form = TemaGeneralForm()
    return render(request, "votaciones/crear_tema.html", {"form": form})


@login_required
def eliminar_tema(request, tema_id):
    empresa = request.user.perfilusuario.empresa
    tema = get_object_or_404(TemaGeneral, id=tema_id, empresa=empresa)
    tema.delete()
    messages.success(request, "Asunto eliminado correctamente.")
    return redirect("lista_temas")

#modulo avisos y notificaciones-->
@login_required
def avisos_lista(request):
    avisos = Aviso.objects.order_by('-fecha_creacion')
    return render(request, 'avisos/avisos_lista.html', {'avisos': avisos})

@login_required
def aviso_crear(request):
    if request.method == 'POST':
        form = AvisoForm(request.POST)
        if form.is_valid():
            aviso = form.save(commit=False)
            aviso.usuario = request.user
            aviso.save()
            return redirect('avisos_lista')
    else:
        form = AvisoForm()
    return render(request, 'avisos/aviso_form.html', {'form': form})

@login_required
def aviso_eliminar(request, aviso_id):
    aviso = get_object_or_404(Aviso, id=aviso_id)
    if request.method == "POST":
        aviso.delete()
        return redirect('avisos_lista')
    return render(request, 'avisos/aviso_confirmar_eliminar.html', {'aviso': aviso})


# Modulo de timbrado de facturas con FACTURAMA
FACTURAMA_USER = os.getenv("FACTURAMA_USER")
FACTURAMA_PASS = os.getenv("FACTURAMA_PASSWORD")


def timbrar_factura_facturama(datos_factura):
    url = (
        "https://apisandbox.facturama.mx/api-lite/3/cfdis"  # URL de sandbox desarrollo
    )
    # url = 'https://api.facturama.mx/'  # URL de producción
    # print("JSON enviado a Facturama:", json.dumps(datos_factura, indent=2))
    # print("FACTURAMA_USER:", FACTURAMA_USER)
    # print("FACTURAMA_PASS:", FACTURAMA_PASS)
    response = requests.post(
        url,
        auth=(FACTURAMA_USER, FACTURAMA_PASS),
        headers={"Content-Type": "application/json"},
        data=json.dumps(datos_factura),
    )
    # print("Status code:", response.status_code)
    # print("Response text:", response.text)
    try:
        return response.json()
    except Exception:
        return {"error": response.text}


def factura_a_json_facturama(
    factura, tax_object="02", payment_method="PUE", payment_form="99"
):
    from decimal import Decimal, ROUND_HALF_UP
    from babel.dates import format_date
    import pytz

    monto = Decimal(factura.monto)
    tasa_iva = Decimal("0.16")
    divisor_iva = Decimal("1.16")

    empresa = factura.empresa
    cliente = factura.cliente

    tz_mx = pytz.timezone("America/Mexico_City")
    fecha_timbrado = timezone.now().astimezone(tz_mx).strftime("%Y-%m-%d %H:%M:%S")

    # --- ADAPTACIÓN PARA AMBOS TIPOS DE FACTURA ---
    # Para Factura normales
    if hasattr(factura, "tipo_cuota") and hasattr(factura, "fecha_vencimiento"):
        descripcion = (
            "Aportación cuota "
            + str(getattr(factura, "tipo_cuota", ""))
            + " "
            + format_date(factura.fecha_vencimiento, "LLLL yyyy", locale="es")
        )
    # Para FacturaOtrosIngresos
    elif hasattr(factura, "tipo_ingreso"):
        descripcion = (
            "Otro ingreso: "
            + str(getattr(factura, "tipo_ingreso", ""))
            + (
                f" - {factura.observaciones}"
                if getattr(factura, "observaciones", "")
                else ""
            )
        )
    else:
        descripcion = factura.observaciones or "Concepto de factura"

    if tax_object == "01":
        # Sin objeto de impuesto: total y subtotal son iguales al monto
        subtotal = monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        item_total = subtotal
        total = subtotal
    else:
        # Con objeto de impuesto: calcula subtotal y desglose de IVA
        subtotal = (monto / divisor_iva).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        iva = (subtotal * tasa_iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        item_total = (subtotal + iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = item_total

    item = {
        "ProductCode": "25173108",
        "Description": descripcion,
        "UnitCode": "E48",
        "Quantity": 1.0,
        "UnitPrice": float(subtotal),
        "Subtotal": float(subtotal),
        "TaxObject": tax_object,
        "Total": float(item_total),
    }

    if tax_object == "02":
        item["Taxes"] = [
            {
                "Total": float(iva),
                "Name": "IVA",
                "Base": float(subtotal),
                "Rate": float(tasa_iva),
                "IsRetention": False,
            }
        ]

    return {
        "CfdiType": "I",
        "PaymentForm": payment_form,
        "PaymentMethod": payment_method,
        "ExpeditionPlace": empresa.codigo_postal,
        "Date": fecha_timbrado,
        "Folio": factura.folio,
        "Issuer": {
            "FiscalRegime": empresa.regimen_fiscal,
            "Rfc": empresa.rfc,
            "Name": empresa.nombre,
        },
        "Receiver": {
            "Rfc": cliente.rfc,
            "CfdiUse": cliente.uso_cfdi,
            "Name": cliente.nombre,
            "FiscalRegime": cliente.regimen_fiscal,
            "TaxZipCode": cliente.codigo_postal,
        },
        "Items": [item],
        "Total": float(total),
    }


@login_required
def timbrar_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    empresa = factura.empresa
    next_url = request.GET.get("next") or request.POST.get("next")
    # Solo permite timbrar si la empresa es PLUS
    if not empresa.es_plus:
        messages.error(
            request, "El timbrado solo está disponible en la versión PLUS del sistema."
        )
        return redirect("lista_facturas")

    if (
        not request.user.is_superuser
        and factura.empresa != request.user.perfilusuario.empresa
    ):
        messages.error(request, "No tienes permiso para timbrar esta factura.")
        return redirect("lista_facturas")

    if factura.uuid:
        messages.info(request, "La factura ya está timbrada.")
        return redirect("lista_facturas")

    if request.method == "POST":
        form = TimbrarFacturaForm(request.POST)
        if form.is_valid():
            tax_object = form.cleaned_data["tax_object"]
            payment_method = form.cleaned_data["payment_method"]
            payment_form = form.cleaned_data["payment_form"]
            datos_json = factura_a_json_facturama(
                factura, tax_object, payment_method, payment_form
            )
            resultado = timbrar_factura_facturama(datos_json)

            if "error" in resultado:
                messages.error(request, f"Error al timbrar: {resultado['error']}")
            else:
                uuid = resultado.get("Uuid") or resultado.get("Complement", {}).get(
                    "TaxStamp", {}
                ).get("Uuid")
                facturama_id = resultado.get("Id")
                if not uuid or not facturama_id:
                    messages.error(request, f"Error inesperado: {resultado}")
                else:
                    factura.uuid = uuid
                    factura.facturama_id = facturama_id
                    factura.save()
                    messages.success(
                        request,
                        "Factura "
                        + factura.folio
                        + " timbrada correctamente. Ahora puedes descargar el PDF y XML.",
                    )
            if next_url:
                return redirect(next_url)
            return redirect("lista_facturas")
    else:
        form = TimbrarFacturaForm()
    next_url = request.GET.get("next")
    return render(
        request,
        "facturacion/timbrar_factura.html",
        {
            "form": form,
            "factura": factura,
            "url_cancelar": next_url,
        },
    )


@login_required
def descargar_factura_timbrada(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    if not factura.uuid:
        messages.error(request, "La factura no está timbrada.")
        return redirect("lista_facturas")

    uuid = factura.uuid
    usuario = os.getenv("FACTURAMA_USER")
    password = os.getenv("FACTURAMA_PASSWORD")

    # URLs para descargar XML y PDF
    xml_url = (
        f"https://apisandbox.facturama.mx/api-lite/3/cfdis/{uuid}/xml"  # desarrollo
    )
    pdf_url = (
        f"https://apisandbox.facturama.mx/api-lite/3/cfdis/{uuid}/pdf"  # desarrollo
    )

    # xml_url = f"https://api.facturama.mx/api-lite/3/cfdis/{uuid}/xml"  #producción
    # pdf_url = f"https://api.facturama.mx/api-lite/3/cfdis/{uuid}/pdf"  #producción

    # Descarga XML
    xml_response = requests.get(xml_url, auth=(usuario, password))
    xml_content = xml_response.content if xml_response.status_code == 200 else None
    print("XML status:", xml_response.status_code)
    print("XML response:", xml_response.text)

    # Descarga PDF
    pdf_response = requests.get(pdf_url, auth=(usuario, password))
    pdf_content = pdf_response.content if pdf_response.status_code == 200 else None
    print("PDF status:", pdf_response.status_code)
    print("PDF response:", pdf_response.text)

    if not xml_content and not pdf_content:
        messages.error(
            request, "No se pudo descargar el PDF ni el XML desde Facturama."
        )
        return redirect("lista_facturas")

    # Prepara ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        if xml_content:
            zip_file.writestr(f"factura_{factura.folio}.xml", xml_content)
        if pdf_content:
            zip_file.writestr(f"factura_{factura.folio}.pdf", pdf_content)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f"attachment; filename=factura_{factura.folio}.zip"
    )
    return response


@staff_member_required
def subir_csd_facturama(request):
    import os

    mensaje = ""
    usuario = os.getenv("FACTURAMA_USER")
    password = os.getenv("FACTURAMA_PASSWORD")
    csds = obtener_csds_facturama(usuario, password)

    if request.method == "POST":
        form = CSDUploadForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.cleaned_data["empresa"]
            rfc = empresa.rfc.upper()
            cer_file = form.cleaned_data["cer_file"]
            key_file = form.cleaned_data["key_file"]
            key_password = form.cleaned_data["key_password"]

            # Valida si ya existe un CSD para ese RFC
            if any(csd.get("Rfc", "").upper() == rfc for csd in csds):
                mensaje = f"Ya existe un CSD cargado para el RFC {rfc}."
            else:
                # Convierte archivos a base64
                cert_b64 = base64.b64encode(cer_file.read()).decode("utf-8")
                key_b64 = base64.b64encode(key_file.read()).decode("utf-8")

                # Llama a la API de Facturama
                url = "https://apisandbox.facturama.mx/api-lite/csds"  # en desarrollo
                # url = "https://api.facturama.mx/api-lite/csds" # en producción
                data = {
                    "Rfc": rfc,
                    "Certificate": cert_b64,
                    "PrivateKey": key_b64,
                    "PrivateKeyPassword": key_password,
                }
                response = requests.post(
                    url,
                    auth=(usuario, password),
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(data),
                )
                if response.status_code == 200:
                    mensaje = (
                        f"CSD cargado correctamente para la empresa {empresa.nombre}."
                    )
                    csds = obtener_csds_facturama(usuario, password)  # Actualiza lista
                else:
                    print("Status code:", response.status_code)
                    print("Response text:", response.text)
                    mensaje = f"Error al cargar CSD: {response.text}"
    else:
        form = CSDUploadForm()
    return render(
        request,
        "facturacion/subir_csd.html",
        {"form": form, "mensaje": mensaje, "csds": csds},
    )


def obtener_csds_facturama(usuario, password):
    url = "https://apisandbox.facturama.mx/api-lite/csds"  # URL de sandbox desarrollo
    # url = "https://api.facturama.mx/api-lite/csds"  # URL de producción
    response = requests.get(url, auth=(usuario, password))
    if response.status_code == 200:
        return response.json()  # Lista de CSDs
    return []


def consultar_cfdis_facturama(
    rfc_issuer=None,
    uuid=None,
    folio_start=None,
    folio_end=None,
    date_start=None,
    date_end=None,
    status="active",
    page=0,
):
    url = "https://apisandbox.facturama.mx/cfdi"  # URL de sandbox desarrollo
    # url = "https://api.facturama.mx/cfdi"  # URL de producción
    params = {"type": "issuedLite", "status": status, "page": page}
    if rfc_issuer:
        params["rfcIssuer"] = rfc_issuer
    if uuid:
        params["uuid"] = uuid
    if folio_start:
        params["folioStart"] = folio_start
    if folio_end:
        params["folioEnd"] = folio_end
    if date_start:
        params["dateStart"] = date_start  # formato: dd/mm/yyyy
    if date_end:
        params["dateEnd"] = date_end  # formato: dd/mm/yyyy

    usuario = os.getenv("FACTURAMA_USER")
    password = os.getenv("FACTURAMA_PASSWORD")
    response = requests.get(url, params=params, auth=(usuario, password))
    if response.status_code == 200:
        return response.json()
    return []


@staff_member_required
def consulta_cfdis_facturama(request):
    empresas = Empresa.objects.all()
    resultados = []
    mensaje = ""
    if request.method == "POST":
        empresa_id = request.POST.get("empresa_id")
        uuid = request.POST.get("uuid")
        folio_start = request.POST.get("folio_start")
        folio_end = request.POST.get("folio_end")
        date_start = request.POST.get("date_start")
        date_end = request.POST.get("date_end")

        empresa = Empresa.objects.filter(id=empresa_id).first()
        rfc_issuer = empresa.rfc if empresa else None

        resultados = consultar_cfdis_facturama(
            rfc_issuer=rfc_issuer,
            uuid=uuid,
            folio_start=folio_start,
            folio_end=folio_end,
            date_start=date_start,
            date_end=date_end,
        )
        if not resultados:
            mensaje = "No se encontraron CFDIs con esos filtros o hubo un error en la consulta."

    return render(
        request,
        "facturacion/consulta_cfdis.html",
        {"empresas": empresas, "resultados": resultados, "mensaje": mensaje},
    )


def descargar_cfdi_facturama(request, id):
    usuario = os.getenv("FACTURAMA_USER")
    password = os.getenv("FACTURAMA_PASSWORD")
    base_url = "https://apisandbox.facturama.mx/cfdi"  # URL de sandbox desarrollo
    # base_url = "https://api.facturama.mx/cfdi"  # URL de producción

    # Descarga XML
    xml_url = f"{base_url}/xml/issuedLite/{id}"
    xml_response = requests.get(xml_url, auth=(usuario, password))
    xml_content = None
    if xml_response.status_code == 200:
        xml_json = xml_response.json()
        xml_content = base64.b64decode(xml_json.get("Content", ""))

    # Descarga PDF
    pdf_url = f"{base_url}/pdf/issuedLite/{id}"
    pdf_response = requests.get(pdf_url, auth=(usuario, password))
    pdf_content = None
    if pdf_response.status_code == 200:
        pdf_json = pdf_response.json()
        pdf_content = base64.b64decode(pdf_json.get("Content", ""))

    if not xml_content and not pdf_content:
        messages.error(
            request, "No se pudo descargar el PDF ni el XML desde Facturama."
        )
        return redirect("consulta_cfdis_facturama")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        if xml_content:
            zip_file.writestr(f"{id}.xml", xml_content)
        if pdf_content:
            zip_file.writestr(f"{id}.pdf", pdf_content)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = f"attachment; filename=cfdi_{id}.zip"
    return response


# timbrar facturas de otros ingresos
@login_required
def timbrar_factura_otros_ingresos(request, pk):
    factura = get_object_or_404(FacturaOtrosIngresos, pk=pk)
    empresa = factura.empresa

    # Solo permite timbrar si la empresa es PLUS
    if not empresa.es_plus:
        messages.error(
            request, "El timbrado solo está disponible en la versión PLUS del sistema."
        )
        return redirect("lista_facturas_otros_ingresos")

    if factura.uuid:
        messages.info(request, "La factura ya está timbrada.")
        return redirect("lista_facturas_otros_ingresos")

    if request.method == "POST":
        form = TimbrarFacturaForm(request.POST)
        if form.is_valid():
            tax_object = form.cleaned_data["tax_object"]
            payment_method = form.cleaned_data["payment_method"]
            payment_form = form.cleaned_data["payment_form"]
            datos_json = factura_a_json_facturama(
                factura, tax_object, payment_method, payment_form
            )
            resultado = timbrar_factura_facturama(datos_json)
            print("Resultado de timbrado:", resultado)
            if "error" in resultado:
                messages.error(request, f"Error al timbrar: {resultado['error']}")
            else:
                uuid = resultado.get("Uuid") or resultado.get("Complement", {}).get(
                    "TaxStamp", {}
                ).get("Uuid")
                facturama_id = resultado.get("Id")
                if not uuid or not facturama_id:
                    messages.error(request, f"Error inesperado: {resultado}")
                else:
                    factura.uuid = uuid
                    factura.facturama_id = facturama_id
                    factura.save()
                    messages.success(
                        request,
                        "Factura "
                        + factura.folio
                        + " timbrada correctamente. Ahora puedes descargar el PDF y XML.",
                    )
            return redirect("lista_facturas_otros_ingresos")
    else:
        form = TimbrarFacturaForm()

    return render(
        request,
        "facturacion/timbrar_factura.html",
        {
            "form": form,
            "factura": factura,
            "url_cancelar": "lista_facturas_otros_ingresos",
        },
    )


# Módulo de timbrado para visitantes
def visitante_timbrar_factura(request, pk):
    visitante_id = request.session.get("visitante_id")
    if not visitante_id:
        return redirect("visitante_login")
    visitante = VisitanteAcceso.objects.get(id=visitante_id)
    factura = get_object_or_404(Factura, pk=pk)
    # Verifica que la factura pertenezca a los locales/áreas del visitante
    if (
        factura.local not in visitante.locales.all()
        and factura.area_comun not in visitante.areas.all()
    ):
        messages.error(request, "No tienes permiso para timbrar esta factura.")
        return redirect("visitante_consulta_facturas")

    empresa = factura.empresa
    if not empresa.es_plus:
        messages.error(
            request,
            "TIMBRADO de Facturas solo está disponible en la versión PLUS. Contacta al administrador del sistema.",
        )
        return redirect("visitante_consulta_facturas")

    if factura.uuid:
        messages.info(request, "La factura ya está timbrada.")
        return redirect("visitante_consulta_facturas")

    if request.method == "POST":
        form = TimbrarFacturaForm(request.POST)
        if form.is_valid():
            tax_object = form.cleaned_data["tax_object"]
            payment_method = form.cleaned_data["payment_method"]
            payment_form = form.cleaned_data["payment_form"]
            datos_json = factura_a_json_facturama(
                factura, tax_object, payment_method, payment_form
            )
            resultado = timbrar_factura_facturama(datos_json)
            print("Resultado de timbrado:", resultado)
            if "error" in resultado:
                messages.error(request, f"Error al timbrar: {resultado['error']}")
            else:
                uuid = resultado.get("Uuid") or resultado.get("Complement", {}).get(
                    "TaxStamp", {}
                ).get("Uuid")
                facturama_id = resultado.get("Id")
                if not uuid or not facturama_id:
                    messages.error(request, f"Error inesperado: {resultado}")
                else:
                    factura.uuid = uuid
                    factura.facturama_id = facturama_id
                    factura.save()
                    messages.success(
                        request,
                        "Factura "
                        + factura.folio
                        + " timbrada correctamente. Ahora puedes descargar el PDF y XML.",
                    )
            return redirect("visitante_consulta_facturas")
    else:
        form = TimbrarFacturaForm()

    return render(
        request,
        "facturacion/timbrar_factura.html",
        {
            "form": form,
            "factura": factura,
            "url_cancelar": "visitante_consulta_facturas",
        },
    )


# Modulo APIS visitantes Flutter

# Decorador para verificar token de visitante
def visitante_token_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token_key = request.headers.get("Authorization", "").replace("Token ", "")
        try:
            token = VisitanteToken.objects.get(key=token_key)
            visitante = token.visitante
            request.visitante = visitante
            return view_func(request, *args, **kwargs)
        except VisitanteToken.DoesNotExist:
            return Response({"error": "Token inválido"}, status=401)
    return _wrapped_view


# APIS registro visitante

# Lista de empresas
@api_view(['GET'])
def api_empresas_lista(request):
    empresas = Empresa.objects.all().order_by('nombre')
    data = [
        {"id": e.id, "nombre": e.nombre}
        for e in empresas
    ]
    return Response(data)

# Lista de locales por empresa
@api_view(['GET'])
def api_locales_por_empresa(request, empresa_id):
    locales = LocalComercial.objects.filter(empresa_id=empresa_id).order_by('numero')
    data = [
        {"id": l.id, "numero": l.numero}
        for l in locales
    ]
    return Response(data)

# Lista de áreas comunes por empresa
@api_view(['GET'])
def api_areas_por_empresa(request, empresa_id):
    areas = AreaComun.objects.filter(empresa_id=empresa_id).order_by('numero')
    data = [
        {"id": a.id, "numero": a.numero}
        for a in areas
    ]
    return Response(data)

# API registro visitante
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def visitante_registro_api(request):
    empresa_id = request.data.get("empresa_id")
    locales_numeros = request.data.getlist("locales_numeros[]")
    areas_numeros = request.data.getlist("areas_numeros[]")
    # Convierte a string
    locales_numeros = [str(num) for num in locales_numeros]
    areas_numeros = [str(num) for num in areas_numeros]
    username = request.data.get("username")
    password = request.data.get("password")
    email = request.data.get("email")
    ine_file = request.FILES.get("ine_file")
    
    # Imprime los valores recibidos para depuración
    # print("empresa_id:", empresa_id)
    # print("locales_numeros:", locales_numeros)
    # print("areas_numeros:", areas_numeros)
    # print("username:", username)
    # print("email:", email)
    # print("ine_file:", ine_file)

    if not empresa_id:
        return Response({"ok": False, "error": "Debes seleccionar una empresa."}, status=400)
    if not ine_file:
        return Response({"ok": False, "error": "Debes subir tu INE."}, status=400)

    try:
        empresa = Empresa.objects.get(id=empresa_id)
    except Empresa.DoesNotExist:
        return Response({"ok": False, "error": "Empresa no encontrada."}, status=404)

    if not locales_numeros and not areas_numeros:
        return Response({"ok": False, "error": "Debes seleccionar al menos un local o un área común."}, status=400)

    if VisitanteAcceso.objects.filter(username=username).exists():
        return Response({"ok": False, "error": "El usuario ya existe."}, status=400)

    locales = []
    areas = []
    errores = []

    # Solo valida locales si hay locales seleccionados y no áreas
    if locales_numeros and not areas_numeros:
        for num in locales_numeros:
            local = LocalComercial.objects.filter(empresa=empresa, numero=num).first()
            if not local:
                errores.append(f"Local {num} no existe en la empresa.")
            elif not local.cliente or local.cliente.email.lower() != email.lower():
                errores.append(f"El correo no coincide con el cliente del local {num}.")
            else:
                locales.append(local)
    # Solo valida áreas si hay áreas seleccionadas y no locales
    elif areas_numeros and not locales_numeros:
        for num in areas_numeros:
            area = AreaComun.objects.filter(empresa=empresa, numero=num).first()
            if not area:
                errores.append(f"Área común {num} no existe en la empresa.")
            elif not area.cliente or area.cliente.email.lower() != email.lower():
                errores.append(f"El correo no coincide con el cliente del área {num}.")
            else:
                areas.append(area)
    # Si hay ambos, valida ambos
    else:
        for num in locales_numeros:
            local = LocalComercial.objects.filter(empresa=empresa, numero=num).first()
            if not local:
                errores.append(f"Local {num} no existe en la empresa.")
            elif not local.cliente or local.cliente.email.lower() != email.lower():
                errores.append(f"El correo no coincide con el cliente del local {num}.")
            else:
                locales.append(local)
        for num in areas_numeros:
            area = AreaComun.objects.filter(empresa=empresa, numero=num).first()
            if not area:
                errores.append(f"Área común {num} no existe en la empresa.")
            elif not area.cliente or area.cliente.email.lower() != email.lower():
                errores.append(f"El correo no coincide con el cliente del área {num}.")
            else:
                areas.append(area)

    if errores:
        return Response({"ok": False, "error": " ".join(errores)}, status=400)

    visitante = VisitanteAcceso.objects.create(
        username=username,
        email=email,
        empresa=empresa
    )
    visitante.set_password(password)
    visitante.save()
    if locales:
        visitante.locales.add(*locales)
    if areas:
        visitante.areas.add(*areas)

    token, _ = VisitanteToken.objects.get_or_create(visitante=visitante)

    asunto = "Nuevo visitante registrado en App"
    mensaje = (
        f"Se ha registrado un nuevo visitante en App.\n\n"
        f"Usuario: {visitante.username}\n"
        f"Email: {visitante.email}\n"
        f"Empresa: {empresa.nombre}\n"
        f"Locales: {', '.join([str(l.numero) for l in locales]) if locales else '-'}\n"
        f"Áreas comunes: {', '.join([str(a.numero) for a in areas]) if areas else '-'}\n"
    )
    # Agrega ambos correos y elimina duplicados
    destinatarios = set()
    if empresa.email:
        destinatarios.add(empresa.email)
    admin_email = getattr(settings, "ADMIN_EMAIL", None)
    if admin_email:
        destinatarios.add(admin_email)

    email_msg = EmailMessage(
        subject=asunto,
        body=mensaje,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=list(destinatarios),
    )
    if ine_file:
        email_msg.attach(ine_file.name, ine_file.read(), ine_file.content_type)
    email_msg.send(fail_silently=True)

    return Response({
        "ok": True,
        "visitante_id": visitante.id,
        "token": token.key,
        "empresa_nombre": empresa.nombre,
        "empresa_email": empresa.email,
        "locales": [l.numero for l in locales],
        "areas": [a.numero for a in areas],
    })


# API login visitante
@api_view(["POST"])
def visitante_login_api(request):
    username = request.data.get("username")
    password = request.data.get("password")
    try:
        visitante = VisitanteAcceso.objects.get(username=username)
        if visitante.check_password(password):
            empresa = None
            # Obtén la empresa del visitante (por local o área)
            if visitante.locales.exists():
                empresa = visitante.locales.first().empresa
            elif visitante.areas.exists():
                empresa = visitante.areas.first().empresa
            stripe_public_key = empresa.stripe_public_key if empresa else ""
            empresa_nombre = empresa.nombre if empresa else ""
            empresa_email = empresa.email if empresa else ""
            # Crea o recupera el token
            token, _ = VisitanteToken.objects.get_or_create(visitante=visitante)
            return Response(
                {
                    "ok": True,
                    "visitante_id": visitante.id,
                    "stripe_public_key": stripe_public_key,
                    "token": token.key,
                    "empresa_nombre": empresa_nombre,
                    "empresa_email": empresa_email,
                }
            )
        else:
            return Response({"ok": False, "error": "Contraseña incorrecta"}, status=400)
    except VisitanteAcceso.DoesNotExist:
        return Response({"ok": False, "error": "Usuario no encontrado"}, status=404)


# API obtener facturas del visitante
@api_view(["GET"])
@visitante_token_required
def visitante_facturas_api(request):
    visitante = request.visitante  # El usuario autenticado por token
    locales = visitante.locales.all()
    areas = visitante.areas.all()
    #facturas = Factura.objects.filter(Q(local__in=locales) | Q(area_comun__in=areas))
    facturas = Factura.objects.filter(Q(local__in=locales) | Q(area_comun__in=areas)) \
        .select_related("cliente", "empresa", "local", "area_comun")
    serializer = FacturaSerializer(facturas, many=True)
    return Response({"facturas": serializer.data})

# API crear Payment Intent con Stripe
@api_view(["POST"])
def create_payment_intent(request):
    amount = request.data.get("amount")
    factura_id = request.data.get("factura_id")
    if not amount:
        return Response({"error": "Monto requerido"}, status=400)
    try:
        factura = Factura.objects.get(id=factura_id)
        empresa = factura.empresa
        stripe.api_key = empresa.stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),  # Stripe usa centavos
            currency="mxn",
            payment_method_types=["card"],
            metadata={"factura_id": factura_id},
        )
        return Response({"client_secret": intent.client_secret})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# API reporte ingresos vs gastos
@api_view(["GET"])
@visitante_token_required
def api_reporte_ingresos_vs_gastos(request):
    visitante = request.visitante
    if not getattr(visitante, "acceso_api_reporte", False):
        return Response({"error": "Acceso denegado"}, status=403)
    
    visitante = request.visitante
    empresa = None
    if visitante.locales.exists():
        empresa = visitante.locales.first().empresa
    elif visitante.areas.exists():
        empresa = visitante.areas.first().empresa

    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    periodo = request.GET.get("periodo")

    #Si no hay ningún filtro, mostrar periodo actual por default
    if not periodo and not fecha_inicio and not fecha_fin and not mes and not anio:
        periodo = "periodo_actual"

    hoy = date.today()
    # Prioridad: periodo > mes/año > fechas manuales
    if periodo == "mes_actual":
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (hoy.replace(day=1) + timedelta(days=32)).replace(
            day=1
        ) - timedelta(days=1)
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
            fecha_inicio =date(anio, mes, 1)
            if mes == 12:
                fecha_fin = date(anio, 12, 31)
            else:
                fecha_fin = date(anio, mes + 1, 1) - timedelta(days=1)
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
            fecha_inicio_dt = datetime.strptime(
                fecha_inicio, "%Y-%m-%d"
            ).date()
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

    # pagos = Pago.objects.exclude(forma_pago="nota_credito").filter(factura__empresa=empresa)
    # pagos_gastos = PagoGasto.objects.all()
    # cobros_otros = CobroOtrosIngresos.objects.select_related("factura", "factura__empresa")
    # gastos_caja_chica = GastoCajaChica.objects.all()
    # vales_caja_chica = ValeCaja.objects.all()

    # Filtra todos los objetos por la empresa del visitante
    pagos = Pago.objects.exclude(forma_pago="nota_credito").filter(factura__empresa=empresa)
    pagos_gastos = PagoGasto.objects.filter(gasto__empresa=empresa)
    cobros_otros = CobroOtrosIngresos.objects.select_related("factura", "factura__empresa").filter(factura__empresa=empresa)
    gastos_caja_chica = GastoCajaChica.objects.filter(fondeo__empresa=empresa)
    vales_caja_chica = ValeCaja.objects.filter(fondeo__empresa=empresa)

    # Aplica filtros de fecha
    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__gte=fecha_inicio)
        pagos_gastos = pagos_gastos.filter(fecha_pago__gte=fecha_inicio)
        cobros_otros = cobros_otros.filter(fecha_cobro__gte=fecha_inicio)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__gte=fecha_inicio)
        vales_caja_chica = vales_caja_chica.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__lte=fecha_fin)
        pagos_gastos = pagos_gastos.filter(fecha_pago__lte=fecha_fin)
        cobros_otros = cobros_otros.filter(fecha_cobro__lte=fecha_fin)
        gastos_caja_chica = gastos_caja_chica.filter(fecha__lte=fecha_fin)
        vales_caja_chica = vales_caja_chica.filter(fecha__lte=fecha_fin)

    total_ingresos = pagos.aggregate(total=Sum("monto"))["total"] or 0
    total_otros_ingresos = cobros_otros.aggregate(total=Sum("monto"))["total"] or 0
    total_ingresos_cobrados = total_ingresos + total_otros_ingresos
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

    saldo = total_ingresos_cobrados - total_egresos

    resultado = {
        "total_ingresos": total_ingresos_cobrados,
        "total_otros_ingresos": total_otros_ingresos,
        "total_gastos_pagados": total_gastos_pagados,
        "total_gastos_caja_chica": total_gastos_caja_chica,
        "total_vales_caja_chica": total_vales_caja_chica,
        "total_egresos": total_egresos,
        "ingresos_por_origen": ingresos_por_origen,
        "gastos_por_tipo": gastos_por_tipo,
        "saldo": saldo,
        "periodo": periodo,
        "mes_letra": mes_letra,
        "empresa_nombre": empresa.nombre if empresa else "",
        "empresa_email": empresa.email if empresa else "",
    }
    return Response(resultado)


#API dashboard cartera vencida
@api_view(['GET'])
@visitante_token_required  
def api_dashboard_saldos_visitante(request):
    visitante = request.visitante
    if not getattr(visitante, "acceso_api_reporte", False):
        return Response({"error": "Acceso denegado"}, status=403)
    
    visitante = request.visitante
    empresa = None
    if visitante.locales.exists():
        empresa = visitante.locales.first().empresa
    elif visitante.areas.exists():
        empresa = visitante.areas.first().empresa

    hoy = timezone.now().date()
    cliente_id = request.GET.get('cliente')
    origen = request.GET.get('origen', 'todos')
    tipo_cuota = request.GET.get('tipo_cuota')
    mes = request.GET.get('mes')
    anio = request.GET.get('anio')

    # Filtro por empresa del visitante
    filtro_empresa = Q(empresa=empresa)

    facturas = Factura.objects.filter(estatus='pendiente').filter(filtro_empresa)
    if cliente_id:
        facturas = facturas.filter(cliente_id=cliente_id)
    if origen == 'local':
        facturas = facturas.filter(local__isnull=False)
    elif origen == 'area':
        facturas = facturas.filter(area_comun__isnull=False)
    if tipo_cuota:
        facturas = facturas.filter(tipo_cuota=tipo_cuota)
    if anio:
        try:
            anio = int(anio)
            facturas = facturas.filter(fecha_vencimiento__year=anio)
        except ValueError:
            pass
    if mes:
        try:
            mes = int(mes)
            facturas = facturas.filter(fecha_vencimiento__month=mes)
        except ValueError:
            pass
          
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
    # Anota el rango de vencimiento en cada factura
    facturas = facturas.annotate(
        rango=Case(
            When(fecha_vencimiento__gt=hoy - timedelta(days=30), then=Value('0_30')),
            When(fecha_vencimiento__gt=hoy - timedelta(days=60), fecha_vencimiento__lte=hoy - timedelta(days=30), then=Value('31_60')),
            When(fecha_vencimiento__gt=hoy - timedelta(days=90), fecha_vencimiento__lte=hoy - timedelta(days=60), then=Value('61_90')),
            When(fecha_vencimiento__gt=hoy - timedelta(days=180), fecha_vencimiento__lte=hoy - timedelta(days=90), then=Value('91_180')),
            When(fecha_vencimiento__lte=hoy - timedelta(days=180), then=Value('181_mas')),
            default=Value('otro'),
            output_field=CharField(),
        )
    )

    # Agrupa y suma en una sola consulta
    saldos = facturas.values('rango').annotate(total=Sum('saldo_pendiente_dash'))
    saldos_dict = {x['rango']: float(x['total']) for x in saldos}
    for key in ['0_30', '31_60', '61_90', '91_180', '181_mas']:
        saldos_dict.setdefault(key, 0.0)

    # Facturas otros ingresos
    facturas_otros = FacturaOtrosIngresos.objects.filter(estatus='pendiente', activo=True).filter(filtro_empresa)
    if cliente_id:
        facturas_otros = facturas_otros.filter(cliente_id=cliente_id)
    if anio:
        try:
            anio = int(anio)
            facturas_otros = facturas_otros.filter(fecha_vencimiento__year=anio)
        except ValueError:
            pass
    if mes:
        try:
            mes = int(mes)
            facturas_otros = facturas_otros.filter(fecha_vencimiento__month=mes)
        except ValueError:
            pass

    cobros_subquery = CobroOtrosIngresos.objects.filter(factura=OuterRef('pk')) \
        .values('factura') \
        .annotate(total_cobrado_dash=Coalesce(Sum('monto'), Value(0, output_field=DecimalField()))) \
        .values('total_cobrado_dash')
    facturas_otros = facturas_otros.annotate(
        total_cobrado_dash=Coalesce(Subquery(cobros_subquery), Value(0, output_field=DecimalField())),
        saldo_pendiente_dash=ExpressionWrapper(
            F('monto') - Coalesce(Subquery(cobros_subquery), Value(0, output_field=DecimalField())),
            output_field=DecimalField()
        )
    )

    # Anota el rango de vencimiento en cada factura otros ingresos
    facturas_otros = facturas_otros.annotate(
        rango=Case(
            When(fecha_vencimiento__gt=hoy - timedelta(days=30), then=Value('0_30')),
            When(fecha_vencimiento__gt=hoy - timedelta(days=60), fecha_vencimiento__lte=hoy - timedelta(days=30), then=Value('31_60')),
            When(fecha_vencimiento__gt=hoy - timedelta(days=90), fecha_vencimiento__lte=hoy - timedelta(days=60), then=Value('61_90')),
            When(fecha_vencimiento__gt=hoy - timedelta(days=180), fecha_vencimiento__lte=hoy - timedelta(days=90), then=Value('91_180')),
            When(fecha_vencimiento__lte=hoy - timedelta(days=180), then=Value('181_mas')),
            default=Value('otro'),
            output_field=CharField(),
        )
    )
    saldos_otros = facturas_otros.values('rango').annotate(total=Sum('saldo_pendiente_dash'))
    saldos_otros_dict = {x['rango']: float(x['total']) for x in saldos_otros}
    for key in ['0_30', '31_60', '61_90', '91_180', '181_mas']:
        saldos_otros_dict.setdefault(key, 0.0)

    # Top 10 adeudos
    top_adeudos = (
        facturas
        .annotate(
            nombre_local_area=Coalesce(
                F('local__numero'),
                F('area_comun__numero'),
                output_field=CharField()
            ),
            tipo_origen=Case(
                When(local__isnull=False, then=Value('Local')),
                When(area_comun__isnull=False, then=Value('Área')),
                default=Value(''),
                output_field=CharField()
            ),
            nombre_cliente=F('cliente__nombre')
        )
        .values('nombre_local_area', 'tipo_origen', 'nombre_cliente')
        .annotate(total=Sum('saldo_pendiente_dash'))
        .order_by('-total')[:10]
    )

    # Serializa resultados
    facturas_data = [
        {
            "folio": f.folio,
            "cliente": f.cliente.nombre if f.cliente else "",
            "empresa": f.empresa.nombre if f.empresa else "",
            "local": f.local.numero if f.local else "",
            "area_comun": f.area_comun.numero if f.area_comun else "",
            "monto": float(f.monto),
            "saldo_pendiente": float(f.saldo_pendiente_dash),
            "fecha_vencimiento": f.fecha_vencimiento,
            "estatus": f.estatus,
        }
        for f in facturas
    ]

    otros_data = [
        {
            "folio": f.folio,
            "cliente": f.cliente.nombre if f.cliente else "",
            "empresa": f.empresa.nombre if f.empresa else "",
            "tipo_ingreso": f.tipo_ingreso.nombre if f.tipo_ingreso else "",
            "monto": float(f.monto),
            "saldo_pendiente": float(f.saldo_pendiente_dash),
            "fecha_vencimiento": f.fecha_vencimiento,
            "estatus": f.estatus,
        }
        for f in facturas_otros
    ]

    return Response({
         "saldos": {
            "0_30": saldos_dict['0_30'] + saldos_otros_dict['0_30'],
            "31_60": saldos_dict['31_60'] + saldos_otros_dict['31_60'],
            "61_90": saldos_dict['61_90'] + saldos_otros_dict['61_90'],
            "91_180": saldos_dict['91_180'] + saldos_otros_dict['91_180'],
            "181_mas": saldos_dict['181_mas'] + saldos_otros_dict['181_mas'],
        },
        "top_adeudos": list(top_adeudos),
        "facturas": facturas_data,
        "facturas_otros": otros_data,
    })

# vista API para avisos
@api_view(['GET'])
@visitante_token_required
def api_avisos_empresa(request):
    visitante = request.visitante
    empresa = None
    if visitante.locales.exists():
        empresa = visitante.locales.first().empresa
    elif visitante.areas.exists():
        empresa = visitante.areas.first().empresa

    if not empresa:
        return Response({"error": "No se encontró empresa asociada al visitante."}, status=400)

    avisos = Aviso.objects.filter(usuario__perfilusuario__empresa=empresa).order_by('-fecha_creacion')
    data = [
        {
            "id": aviso.id,
            "titulo": aviso.titulo,
            "mensaje": aviso.mensaje,
            "fecha_creacion": aviso.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
        }
        for aviso in avisos
    ]
    return Response(data)


# conciliación bancaria
@login_required
def subir_estado_cuenta(request):
    conciliados_cargos = []
    conciliados_abonos = []
    no_conciliados_cargos = []
    no_conciliados_abonos = []
    periodo = None
    error = None

    if request.method == "POST":
        form = EstadoCuentaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES.get("archivo")
            if not archivo:
                error = "No se recibió ningún archivo."
            else:
                movimientos_banco = []
                try:
                    text = archivo.read().decode("utf-8", errors="ignore")
                    reader = csv.DictReader(io.StringIO(text))
                    for row in reader:
                        try:
                            fecha = datetime.strptime(row["fecha"], "%d/%m/%Y").date()
                        except ValueError:
                            fecha = datetime.strptime(row["fecha"], "%Y-%m-%d").date()
                        cargo = float(row.get("cargo", 0) or 0)
                        abono = float(row.get("abono", 0) or 0)
                        descripcion = row.get("descripcion", "")
                        movimientos_banco.append(
                            {
                                "fecha": fecha,
                                "cargo": cargo,
                                "abono": abono,
                                "descripcion": descripcion,
                                "usado": False,
                            }
                        )
                except Exception as e:
                    error = f"Error al leer el archivo: {e}"

                if movimientos_banco:
                    fecha_min = min(m["fecha"] for m in movimientos_banco)
                    fecha_max = max(m["fecha"] for m in movimientos_banco)
                    periodo = f"{fecha_min.strftime('%d/%m/%Y')} al {fecha_max.strftime('%d/%m/%Y')}"
                    empresa = request.user.perfilusuario.empresa

                    # 1. Movimientos del sistema en el periodo
                    pagos_cuotas = list(
                        Pago.objects.filter(
                            factura__empresa=empresa,
                            fecha_pago__gte=fecha_min,
                            fecha_pago__lte=fecha_max,
                        )
                    )
                    pagos_otros = list(
                        CobroOtrosIngresos.objects.filter(
                            factura__empresa=empresa,
                            fecha_cobro__gte=fecha_min,
                            fecha_cobro__lte=fecha_max,
                        )
                    )
                    pagos_gastos = list(
                        PagoGasto.objects.filter(
                            gasto__empresa=empresa,
                            fecha_pago__gte=fecha_min,
                            fecha_pago__lte=fecha_max,
                        )
                    )
                    fondeos = list(
                        FondeoCajaChica.objects.filter(
                            empresa=empresa, fecha__gte=fecha_min, fecha__lte=fecha_max
                        )
                    )

                    # 2. Conciliación de abonos (cuotas y otros ingresos)
                    for pago in pagos_cuotas:
                        encontrado = next(
                            (
                                b
                                for b in movimientos_banco
                                if not b["usado"]
                                and b["abono"] == pago.monto
                                and b["fecha"] == pago.fecha_pago
                            ),
                            None,
                        )
                        mov = {
                            "fecha": pago.fecha_pago,
                            "abono": pago.monto,
                            "cargo": 0,
                            "descripcion": f'Pago cuota {getattr(pago.factura, "folio", "")}',
                            "tipo": "Pago cuota",
                        }
                        if encontrado:
                            conciliados_abonos.append(mov)
                            encontrado["usado"] = True
                        else:
                            no_conciliados_abonos.append(mov)

                    for cobro in pagos_otros:
                        encontrado = next(
                            (
                                b
                                for b in movimientos_banco
                                if not b["usado"]
                                and b["abono"] == cobro.monto
                                and b["fecha"] == cobro.fecha_cobro
                            ),
                            None,
                        )
                        mov = {
                            "fecha": cobro.fecha_cobro,
                            "abono": cobro.monto,
                            "cargo": 0,
                            "descripcion": f'Pago otros ingresos {getattr(cobro.factura, "folio", "")}',
                            "tipo": "Pago otros ingresos",
                        }
                        if encontrado:
                            conciliados_abonos.append(mov)
                            encontrado["usado"] = True
                        else:
                            no_conciliados_abonos.append(mov)

                    # 3. Conciliación de cargos (gastos y fondeos)
                    for gasto in pagos_gastos:
                        encontrado = next(
                            (
                                b
                                for b in movimientos_banco
                                if not b["usado"]
                                and b["cargo"] == gasto.monto
                                and b["fecha"] == gasto.fecha_pago
                            ),
                            None,
                        )
                        mov = {
                            "fecha": gasto.fecha_pago,
                            "cargo": gasto.monto,
                            "abono": 0,
                            "descripcion": f'Pago gasto {getattr(gasto.gasto, "referencia", "")}',
                            "tipo": "Pago gasto",
                        }
                        if encontrado:
                            conciliados_cargos.append(mov)
                            encontrado["usado"] = True
                        else:
                            no_conciliados_cargos.append(mov)

                    for fondeo in fondeos:
                        encontrado = next(
                            (
                                b
                                for b in movimientos_banco
                                if not b["usado"]
                                and b["cargo"] == fondeo.importe_cheque
                                and b["fecha"] == fondeo.fecha
                            ),
                            None,
                        )
                        mov = {
                            "fecha": fondeo.fecha,
                            "cargo": fondeo.importe_cheque,
                            "abono": 0,
                            "descripcion": "Fondeo caja chica",
                            "tipo": "Fondeo caja chica",
                        }
                        if encontrado:
                            conciliados_cargos.append(mov)
                            encontrado["usado"] = True
                        else:
                            no_conciliados_cargos.append(mov)

    else:
        form = EstadoCuentaUploadForm()

    # Totales
    total_conciliado_cargos = sum(mov["cargo"] for mov in conciliados_cargos)
    total_conciliado_abonos = sum(mov["abono"] for mov in conciliados_abonos)
    total_no_conciliado_cargos = sum(mov["cargo"] for mov in no_conciliados_cargos)
    total_no_conciliado_abonos = sum(mov["abono"] for mov in no_conciliados_abonos)

    return render(
        request,
        "conciliacion/estado_cuenta_vista.html",
        {
            "form": form,
            "periodo": periodo,
            "error": error,
            "conciliados_cargos": conciliados_cargos,
            "conciliados_abonos": conciliados_abonos,
            "no_conciliados_cargos": no_conciliados_cargos,
            "no_conciliados_abonos": no_conciliados_abonos,
            "total_conciliado_cargos": total_conciliado_cargos,
            "total_conciliado_abonos": total_conciliado_abonos,
            "total_no_conciliado_cargos": total_no_conciliado_cargos,
            "total_no_conciliado_abonos": total_no_conciliado_abonos,
        },
    )


@login_required
def descargar_plantilla_estado_cuenta(request):
    contenido = (
        "fecha,cargo,abono,descripcion\n"
        "01/10/2025,0,1500.00,Pago cuota octubre\n"
        "02/10/2025,500.00,0,Pago gasto limpieza\n"
        "03/10/2025,0,2000.00,Fondeo caja chica\n"
        "04/10/2025,0,1200.00,Pago otros ingresos\n"
    )
    response = HttpResponse(contenido, content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=plantilla_estado_cuenta.csv"
    return response



#recordatorios morosidad
@login_required
def enviar_recordatorio_morosidad(request):
    local_id = request.GET.get("local_id")
    area_id = request.GET.get("area_id")

    # Validación de parámetros
    if local_id and not local_id.isdigit():
        messages.error(request, "ID de local inválido.")
        return redirect('lista_facturas')
    if area_id and not area_id.isdigit():
        messages.error(request, "ID de área común inválido.")
        return redirect('lista_facturas')

    if local_id:
        local_id = int(local_id)
        facturas = Factura.objects.filter(local_id=local_id, estatus='pendiente')
        facturas = [f for f in facturas if f.saldo_pendiente > 0]
        if not facturas:
            messages.warning(request, "No hay adeudos pendientes para este local.")
            return redirect('lista_facturas')
        cliente = facturas[0].cliente
        email = cliente.email
        email_empresa = facturas[0].empresa.email if facturas[0].empresa else ""
        if not email:
            messages.error(request, "El cliente no tiene email registrado.")
            return redirect('lista_facturas')
        empresa_nombre = facturas[0].empresa.nombre if facturas[0].empresa else ""
        mensaje = f"{empresa_nombre}\n\nEstimado cliente {cliente.nombre}, tiene los siguientes adeudos en cuotas:\n\n"
        total = 0
        def formato_importe(importe):
            return "${:,.2f}".format(round(importe, 2))
        for factura in facturas:
            ubicacion = f"Local: {factura.local.numero}" if factura.local else "Sin ubicación"
            mensaje += f"- Folio: {factura.folio},{ubicacion}, Monto pendiente: {formato_importe(factura.saldo_pendiente)}\n"
            total += factura.saldo_pendiente
        mensaje += f"\nTotal pendiente: {formato_importe(total)}\nPor favor realice su pago lo antes posible. \n\n Si ya realizo su pago envie su comprobante al correo: {email_empresa}"
        send_mail(
            subject="Recordatorio de cuotas pendientes de pago",
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        messages.success(request, "Recordatorio enviado correctamente al cliente del local.")
        return redirect('lista_facturas')

    elif area_id:
        area_id = int(area_id)
        facturas = Factura.objects.filter(area_comun_id=area_id, estatus='pendiente')
        facturas = [f for f in facturas if f.saldo_pendiente > 0]
        if not facturas:
            messages.warning(request, "No hay adeudos pendientes para esta área común.")
            return redirect('lista_facturas')
        cliente = facturas[0].cliente
        email = cliente.email
        if not email:
            messages.error(request, "El cliente no tiene email registrado.")
            return redirect('lista_facturas')
        empresa_nombre = facturas[0].empresa.nombre if facturas[0].empresa else ""
        email_empresa = facturas[0].empresa.email if facturas[0].empresa else ""
        mensaje = f"{empresa_nombre}\n\nEstimado cliente {cliente.nombre}, tiene los siguientes adeudos en cuotas de área común:\n\n"
        total = 0
        def formato_importe(importe):
            return "${:,.2f}".format(round(importe, 2))
        for factura in facturas:
            ubicacion = f"Área común: {factura.area_comun.numero}" if factura.area_comun else "Sin ubicación"
            mensaje += f"- Folio: {factura.folio},{ubicacion}, Monto pendiente: {formato_importe(factura.saldo_pendiente)}\n"
            total += factura.saldo_pendiente
        mensaje += f"\nTotal pendiente: {formato_importe(total)}\nPor favor realice su pago lo antes posible.\n\n Si ya realizo su pago envie su comprobante al correo: {email_empresa}"
        send_mail(
            subject="Recordatorio de cuotas pendientes de pago (Área común)",
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        messages.success(request, "Recordatorio enviado correctamente al cliente del área común.")
        return redirect('lista_facturas')

    else:
        messages.error(request, "Debes seleccionar un local o un área común antes de enviar el recordatorio.")
        return redirect('lista_facturas')