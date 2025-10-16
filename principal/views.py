
import csv
from decimal import ROUND_HALF_UP
import os
from urllib import response
from uuid import uuid4
import uuid
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
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
from .models import Evento, PerfilUsuario, TemaGeneral, VisitanteAcceso, VotacionCorreo
import json
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from datetime import date
import stripe
from .models import TicketMantenimiento
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import TicketMantenimiento, SeguimientoTicket
from django.contrib.auth.hashers import check_password
from django.urls import reverse
from django.conf import settings
import requests



stripe.api_key = settings.STRIPE_SECRET_KEY

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


#Configuración del sistema
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
        return render(request, "respaldo_empresas.html", {
            "empresas": Empresa.objects.all(),
            "error": "Empresa no encontrada."
        })

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Borra hoja por defecto

    # CLIENTES
    ws = wb.create_sheet("Clientes")
    ws.append(["id", "nombre", "rfc", "telefono", "email", "activo"])
    for c in Cliente.objects.filter(empresa=empresa):
        ws.append([c.id, c.nombre, c.rfc, c.telefono, c.email, c.activo])

    # LOCALES
    ws = wb.create_sheet("Locales")
    ws.append([
        "id", "numero", "cliente", "ubicacion", "superficie_m2", "cuota",
        "status", "activo", "observaciones"
    ])
    for l in LocalComercial.objects.filter(empresa=empresa):
        ws.append([
            l.id,
            l.numero,
            l.cliente.nombre if l.cliente else "",
            l.ubicacion,
            l.superficie_m2,
            l.cuota,
            l.status,
            l.activo,
            l.observaciones,
        ])

    # ÁREAS COMUNES
    ws = wb.create_sheet("Áreas Comunes")
    ws.append([
        "cliente", "numero", "cuota", "ubicacion", "superficie_m2", "status",
        "fecha_inicial", "fecha_fin", "activo", "observaciones"
    ])
    for a in AreaComun.objects.filter(empresa=empresa):
        ws.append([
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
        ])

    # FACTURAS
    ws = wb.create_sheet("Facturas")
    ws.append([
        "folio", "cliente", "local", "area_comun", "monto",
        "fecha_emision", "fecha_vencimiento", "estatus"
    ])
    for f in Factura.objects.filter(empresa=empresa):
        ws.append([
            f.folio,
            f.cliente.nombre if f.cliente else "",
            f.local.numero if f.local else "",
            f.area_comun.numero if f.area_comun else "",
            float(f.monto),
            str(f.fecha_emision),
            str(f.fecha_vencimiento),
            f.estatus,
        ])

    # PAGOS
    ws = wb.create_sheet("Pagos")
    ws.append(["id", "factura", "fecha_pago", "monto", "registrado_por"])
    for p in Pago.objects.filter(factura__empresa=empresa):
        ws.append([
            p.id,
            p.factura.folio if p.factura else "",
            str(p.fecha_pago),
            float(p.monto),
            p.registrado_por.get_full_name() if p.registrado_por else "",
        ])

    # GASTOS
    ws = wb.create_sheet("Gastos")
    ws.append([
        "id", "proveedor", "empleado", "descripcion", "monto", "tipo_gasto", "fecha"
    ])
    for g in Gasto.objects.filter(empresa=empresa):
        ws.append([
            g.id,
            str(g.proveedor) if g.proveedor else "",
            str(g.empleado) if g.empleado else "",
            g.descripcion,
            float(g.monto),
            str(g.tipo_gasto) if g.tipo_gasto else "",
            str(g.fecha),
        ])

    # PAGOS GASTOS
    ws = wb.create_sheet("Pagos Gastos")
    ws.append(["id", "referencia", "fecha_pago", "monto", "registrado_por"])
    for g in Gasto.objects.filter(empresa=empresa):
        for pago in g.pagos.all():
            ws.append([
                pago.id,
                pago.referencia,
                str(pago.fecha_pago),
                float(pago.monto),
                pago.registrado_por.get_full_name() if pago.registrado_por else "",
            ])

    # PRESUPUESTOS
    ws = wb.create_sheet("Presupuestos")
    ws.append([
        "id", "empresa", "grupo", "subgrupo", "tipo_gasto", "anio", "mes", "monto"
    ])
    for p in Presupuesto.objects.filter(empresa=empresa):
        ws.append([
            p.id,
            p.empresa.nombre if p.empresa else "",
            str(p.grupo) if p.grupo else "",
            str(p.subgrupo) if p.subgrupo else "",
            str(p.tipo_gasto) if p.tipo_gasto else "",
            p.anio,
            p.mes,
            float(p.monto),
        ])
        # PRESUPUESTOS INGRESOS
    ws = wb.create_sheet("Presupuestos Ingresos")
    ws.append([
        "id", "empresa", "tipo_ingreso", "anio", "mes", "monto"
    ])
    for p in PresupuestoIngreso.objects.filter(empresa=empresa):
        ws.append([
            p.id,
            p.empresa.nombre if p.empresa else "",
            str(p.tipo_ingreso) if hasattr(p, "tipo_ingreso") else "",
            p.anio,
            p.mes,
            float(p.monto),
        ])

    # EMPLEADOS
    ws = wb.create_sheet("Empleados")
    ws.append(["id", "nombre", "email", "telefono", "puesto", "activo"])
    for e in Empleado.objects.filter(empresa=empresa):
        ws.append([e.id, e.nombre, e.email, e.telefono, e.puesto, e.activo])

    # PROVEEDORES
    ws = wb.create_sheet("Proveedores")
    ws.append(["id", "nombre", "rfc", "telefono", "email", "activo"])
    for p in Proveedor.objects.filter(empresa=empresa):
        ws.append([
            p.id,
            str(p.nombre),
            p.rfc,
            p.telefono,
            p.email,
            p.activo
        ])

    # OTROS INGRESOS
    ws = wb.create_sheet("Otros Ingresos")
    ws.append([
        "id", "folio", "cliente", "tipo_ingreso", "monto", "saldo", "fecha_emision",
        "fecha_vencimiento", "estatus", "observaciones"
    ])
    for f in FacturaOtrosIngresos.objects.filter(empresa=empresa):
        ws.append([
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
        ])

    # PAGOS OTROS INGRESOS
    ws = wb.create_sheet("Pagos Otros Ingresos")
    ws.append(["id", "factura", "fecha_pago", "monto", "registrado_por"])
    for p in CobroOtrosIngresos.objects.filter(factura__empresa=empresa):
        ws.append([
            p.id,
            p.factura.folio if p.factura else "",
            str(p.fecha_pago),
            float(p.monto),
            p.registrado_por.get_full_name() if p.registrado_por else "",
        ])    

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


# Webhook de Stripe pago sistema de suscripciones
@csrf_exempt
def stripe_webhook(request):
    import stripe
    from django.http import HttpResponse
    from django.conf import settings
    from .models import PerfilUsuario
    from django.contrib.auth.models import User

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        print("Error Stripe:", e)
        return HttpResponse(status=400)

    # Activación inicial de suscripción
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        email = session.get('customer_details', {}).get('email')
        if customer_id:
            try:
                perfil = PerfilUsuario.objects.get(stripe_customer_id=customer_id)
                user = perfil.usuario
                user.is_active = True
                perfil.tipo_usuario = 'pago'
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
                        perfil.tipo_usuario = 'pago'
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
    if event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        if customer_id:
            try:
                perfil = PerfilUsuario.objects.get(stripe_customer_id=customer_id)
                perfil.tipo_usuario = 'pago'
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
                "price":"price_1RxsU7PYnlfwKZQH4u5DJ7aH",
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
            perfil.tipo_usuario = 'demo'  # O el estado que corresponda
            perfil.save()
            return JsonResponse({'status': 'cancelada'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'detail': str(e)}, status=400)
    return JsonResponse({'status': 'no encontrada'}, status=404)

@require_POST
@login_required
def guardar_datos_empresa(request):
    perfil = request.user.perfilusuario
    empresa = perfil.empresa
    nuevo_rfc = request.POST.get('rfc_empresa', '').strip()

    if Empresa.objects.filter(rfc=nuevo_rfc).exclude(id=empresa.id).exists():
        messages.error(request, "El RFC ingresado ya está registrado en otra empresa.")
        return redirect('bienvenida')
    
    empresa.nombre = request.POST.get('nombre_empresa', '')
    empresa.rfc = nuevo_rfc
    empresa.direccion = request.POST.get('direccion_empresa', '')
    empresa.email = request.POST.get('email_empresa', '')
    empresa.telefono = request.POST.get('telefono_empresa', '')
    empresa.cuenta_bancaria = request.POST.get('cuenta_bancaria', '')
    empresa.numero_cuenta = request.POST.get('numero_cuenta', '')
    try:
        empresa.saldo_inicial = float(request.POST.get('saldo_inicial', 0.00))
    except ValueError:
        empresa.saldo_inicial = 0.00
    empresa.save()
    perfil.mostrar_wizard = False
    perfil.save()
    messages.success(request, "¡Datos de empresa actualizados correctamente!")
    return redirect('bienvenida')


#MODULO DE TICKETS DE MANTENIMIENTO-->   
@login_required
def crear_ticket(request):
    empresa = request.user.perfilusuario.empresa
    empleados = Empleado.objects.filter(empresa=empresa, activo=True)
    if request.method == 'POST':
        titulo = request.POST['titulo']
        descripcion = request.POST['descripcion']
        empleado_id = request.POST['empleado_asignado']
        empleado = Empleado.objects.get(id=empleado_id)
        ticket = TicketMantenimiento.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            empleado_asignado=empleado
        )
        # Enviar correo si el empleado tiene email
        if empleado.email:
            send_mail(
                'Nuevo ticket de mantenimiento asignado',
                f'Se te ha asignado el ticket: {titulo}\nDescripción: {descripcion}',
                'soporte@tuempresa.com',
                [empleado.email],
                fail_silently=True,
            )
        # Aquí puedes integrar WhatsApp con una API externa
        return redirect('lista_tickets')
    return render(request, 'mantenimiento/crear_ticket.html', {'empleados': empleados})

@login_required
def actualizar_ticket(request, ticket_id):
    ticket = TicketMantenimiento.objects.get(id=ticket_id)
    if request.method == 'POST':
        ticket.estado = request.POST['estado']
        ticket.solucion = request.POST.get('solucion', '')
        if ticket.estado == 'resuelto':
            ticket.fecha_solucion = timezone.now()
        ticket.save()
        return redirect('detalle_ticket', ticket_id=ticket.id)
    return render(request, 'mantenimiento/actualizar_ticket.html', {'ticket': ticket})

@login_required
def agregar_seguimiento(request, ticket_id):
    ticket = get_object_or_404(TicketMantenimiento, id=ticket_id)
    if request.method == 'POST':
        comentario = request.POST['comentario']
        SeguimientoTicket.objects.create(
            ticket=ticket,
            usuario=request.user,
            comentario=comentario
        )
    return redirect('detalle_ticket', ticket_id=ticket.id)
    
@login_required
def detalle_ticket(request, ticket_id):
    ticket = TicketMantenimiento.objects.get(id=ticket_id)
    seguimientos = ticket.seguimientos.order_by('-fecha')
    return render(request, 'mantenimiento/detalle_ticket.html', {
        'ticket': ticket,
        'seguimientos': seguimientos
    })

@login_required
def tickets_asignados(request):
    empresa = request.user.perfilusuario.empresa
    empleados = Empleado.objects.filter(empresa=empresa, activo=True)
    empleado_id = request.GET.get('empleado_id')
    tickets = []
    empleado_seleccionado = None
    if empleado_id:
        empleado_seleccionado = Empleado.objects.filter(id=empleado_id, empresa=empresa).first()
        tickets = TicketMantenimiento.objects.filter(empleado_asignado=empleado_seleccionado)
    return render(request, 'mantenimiento/tickets_asignados.html', {
        'empleados': empleados,
        'tickets': tickets,
        'empleado_seleccionado': empleado_seleccionado,
    })

@login_required
def lista_tickets(request):
    if request.user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            tickets = TicketMantenimiento.objects.filter(empleado_asignado__empresa_id=empresa_id).order_by('-fecha_creacion')
        else:
            tickets = TicketMantenimiento.objects.all().order_by('-fecha_creacion')
    else:
        empresa = request.user.perfilusuario.empresa
        tickets = TicketMantenimiento.objects.filter(empleado_asignado__empresa=empresa).order_by('-fecha_creacion')
    return render(request, 'mantenimiento/lista_tickets.html', {'tickets': tickets})

@login_required
def seleccionar_empresa(request):
    if not request.user.is_superuser:
        return redirect('bienvenida')  # O la vista normal

    if request.method == 'POST':
        empresa_id = request.POST.get('empresa')
        if empresa_id:
            request.session['empresa_id'] = empresa_id
            return redirect('bienvenida')  # O la vista principal
    empresas = Empresa.objects.all()
    return render(request, 'seleccionar_empresa.html', {'empresas': empresas})


#modulo visitantes consulta adeudos y pagos de facturas-->
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
    local_id = request.GET.get('local_id')
    area_id = request.GET.get('area_id')

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
    # Calcula total pendiente y total cobrado
    total_pendiente = sum(f.saldo_pendiente for f in facturas if f.estatus == 'pendiente')
    total_cobrado = sum(f.monto for f in facturas if f.estatus == 'cobrada')

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
        }
    )

def visitante_logout(request):
    request.session.flush()
    return redirect('visitante_login')

def visitante_factura_detalle(request, factura_id):
    visitante_id = request.session.get("visitante_id")
    if not visitante_id:
        return redirect("visitante_login")
    visitante = VisitanteAcceso.objects.get(id=visitante_id)
    factura = get_object_or_404(Factura, id=factura_id)
    # Verifica que la factura pertenezca a los locales/áreas del visitante
    if factura.local not in visitante.locales.all() and factura.area_comun not in visitante.areas.all():
        return redirect("visitante_consulta_facturas")
    cobros = factura.pagos.all()
    return render(request, "facturacion/facturas_detalle.html",
                   {"factura": factura, "cobros": cobros, "es_visitante": True})


# Pago con Stripe para visitantes
def stripe_checkout_visitante(request, factura_id):
    from facturacion.models import Factura
    factura = get_object_or_404(Factura, id=factura_id)
    empresa = factura.empresa

    # Verifica que la empresa tenga las claves de Stripe configuradas
    if not (empresa.stripe_secret_key and empresa.stripe_public_key and empresa.stripe_webhook_secret):
        messages.error(
            request,
            " PAGO EN LINEA no esta configurado. Contacta al administrador del sistema."
        )
        return redirect('visitante_consulta_facturas')
    elif not empresa.es_plus:
        messages.error(
            request,
            " PAGO EN LINEA solo está disponible en la versión PLUS del sistema.Contacta al administrador del sistema."
        )
        return redirect('visitante_consulta_facturas')  # O la vista/lista que corresponda
    
    
    stripe.api_key = empresa.stripe_secret_key  # <-- Usa la clave secreta de la empresa

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'mxn',
                'product_data': {
                    'name': f'Pago factura {factura.folio}',
                },
                'unit_amount': int(factura.saldo_pendiente * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/visitante/consulta/?pagook=1'),
        cancel_url=request.build_absolute_uri('/visitante/consulta/?pagocancel=1'),
        metadata={'factura_id': factura.id}
    )
    return redirect(session.url)

@csrf_exempt
def stripe_webhook_visitante(request):
    import logging
    import stripe
    import json
    from facturacion.models import Factura, Pago
    from django.utils import timezone

    logger = logging.getLogger("django")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    

    # 1. Carga el evento para saber el tipo
    try:
        event_data = json.loads(payload)
        event_type = event_data.get("type")
    except Exception as e:
        logger.error(f"Error leyendo el evento Stripe: {e}")
        logger.error(f"Factura no encontrada: {factura_id}")
        return HttpResponse(status=400)

    # 2. Solo procesa checkout.session.completed
    if event_type != "checkout.session.completed":
        logger.info(f"Ignorando evento Stripe tipo: {event_type}")
        return JsonResponse({'status': 'ignored'})

    # 3. Ahora sí, procesa normalmente
    try:
        session = event_data['data']['object']
        factura_id = session.get('metadata', {}).get('factura_id')
        logger.error(f"Buscando factura con id: {factura_id}")
        print(f"Buscando factura con id: {factura_id}")
        if not factura_id:
            logger.error("No se encontró factura_id en metadata.")
            return HttpResponse(status=400)
        factura = Factura.objects.select_related('empresa').get(id=int(factura_id))
        empresa = factura.empresa
        endpoint_secret = empresa.stripe_webhook_secret
    except Exception as e:
        logger.error(f"Error extrayendo factura/empresa: {e}")
        return HttpResponse(status=400)

    # 4. Valida la firma
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return HttpResponse(status=400)

    logger.info(f"Stripe event type: {event['type']}")

    session = event['data']['object']
    logger.info(f"Webhook session metadata: {session.get('metadata')}")
    factura_id = session['metadata'].get('factura_id') if session.get('metadata') else None
    logger.info(f"Factura ID recibido: {factura_id}")
    if factura_id:
        try:
            factura = Factura.objects.get(id=int(factura_id))
            monto_pagado = session.get('amount_total', 0) / 100.0
            Pago.objects.create(
                factura=factura,
                monto=monto_pagado,
                forma_pago='stripe',
                fecha_pago=timezone.now(),
                registrado_por=None,
                observaciones=f"Pago en línea, ID transacción: {session.get('payment_intent')}"
            )
            factura.actualizar_estatus()
            factura.save()
        except Factura.DoesNotExist:
            logger.error(f"Factura no encontrada: {factura_id}")
    return JsonResponse({'status': 'ok'})


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
        votacion = VotacionCorreo.objects.create(
            tema=tema,
            email=correo,
            token=token
        )
        url_si = request.build_absolute_uri(
            reverse('votar_tema_correo', args=[token, 'si'])
        )
        url_no = request.build_absolute_uri(
            reverse('votar_tema_correo', args=[token, 'no'])    
        )
        url_abstencion = request.build_absolute_uri(
            reverse('votar_tema_correo', args=[token, 'abstencion'])
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
            message="Te invitamos a votar. Si no ves los botones, copia y pega los enlaces en tu navegador:\nSí: {0}\nNo: {1}".format(url_si, url_no),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[correo],
            html_message=mensaje
        )

def votar_tema_correo(request, token, respuesta):
    votacion = get_object_or_404(VotacionCorreo, token=token)
    if votacion.voto is not None:
        return HttpResponse("Ya has votado.")
    if respuesta not in ['si', 'no', 'abstencion']:
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
    si = votos.filter(voto='si').count()
    no = votos.filter(voto='no').count()
    abstencion = votos.filter(voto='abstencion').count()
    pendientes = votos.filter(voto__isnull=True).count()
    return render(request, 'votaciones/resultados_votacion.html', {
        'tema': tema,
        'total': total,
        'si': si,
        'no': no,
        'abstencion': abstencion,
        'pendientes': pendientes,
        'votos': votos,
    })

@login_required
def lista_temas(request):
    empresa = request.user.perfilusuario.empresa
    temas = TemaGeneral.objects.filter(empresa=empresa).order_by('-fecha_creacion')
    return render(request, 'votaciones/lista_temas.html', {'temas': temas})

@login_required
def crear_tema_y_enviar(request):
    empresa = request.user.perfilusuario.empresa
    tema_id = request.GET.get('tema_id')
    tema = None
    if tema_id:
        tema = get_object_or_404(TemaGeneral, id=tema_id, empresa=empresa)
    if request.method == 'POST':
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
            lista_correos = [c.strip() for c in form.cleaned_data['correos'].split(',') if c.strip()]
            enviar_votacion(tema, lista_correos, request)
            messages.success(request, "Asunto creado y correos enviados.")
            return redirect('lista_temas')
    else:
        if tema:
            # Precarga los correos anteriores si existen votaciones previas
            correos_previos = ', '.join(
                VotacionCorreo.objects.filter(tema=tema).values_list('email', flat=True)
            )
            form = TemaGeneralForm(instance=tema, initial={'correos': correos_previos})
        else:
            form = TemaGeneralForm()
    return render(request, 'votaciones/crear_tema.html', {'form': form})

@login_required
def eliminar_tema(request, tema_id):
    empresa = request.user.perfilusuario.empresa
    tema = get_object_or_404(TemaGeneral, id=tema_id, empresa=empresa)
    tema.delete()
    messages.success(request, "Asunto eliminado correctamente.")
    return redirect('lista_temas')


# Módulo de conciliación bancaria
def conciliar_estado_cuenta(ruta_archivo, empresa):
    from facturacion.models import Factura, FacturaOtrosIngresos
    from caja_chica.models import FondeoCajaChica
    from gastos.models import Gasto
    from datetime import datetime

    conciliados = []
    no_conciliados = []
    fechas = []
    movimientos_csv = []

    # 1. Lee el archivo y guarda fechas y movimientos
    with open(ruta_archivo, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            fecha_str = row['fecha']
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                continue  # Salta filas con fecha inválida
            fechas.append(fecha)
            movimientos_csv.append({
                'fecha': fecha,
                'monto': float(row['monto']),
                'descripcion': row.get('descripcion', '')
            })

    if not fechas:
        return {
            'conciliados': [],
            'no_conciliados': movimientos_csv,
            'fecha_min': None,
            'fecha_max': None,
            'error': 'No se detectaron fechas válidas en el archivo.'
        }

    fecha_min = min(fechas)
    fecha_max = max(fechas)

    # 2. Filtra movimientos del sistema solo dentro del rango de fechas
    facturas = Factura.objects.filter(
        empresa=empresa,
        fecha_emision__gte=fecha_min,
        fecha_emision__lte=fecha_max,
        estatus='pendiente'
    )
    otros_ingresos = FacturaOtrosIngresos.objects.filter(
        empresa=empresa,
        fecha_emision__gte=fecha_min,
        fecha_emision__lte=fecha_max,
        estatus='pendiente'
    )
    gastos = Gasto.objects.filter(
        empresa=empresa,
        fecha__gte=fecha_min,
        fecha__lte=fecha_max,
        estatus='pendiente'
    )
    fondeos = FondeoCajaChica.objects.filter(
        empresa=empresa,
        fecha__gte=fecha_min,
        fecha__lte=fecha_max
    )

    # 3. Procesa cada movimiento del CSV
    for mov in movimientos_csv:
        monto = mov['monto']
        descripcion = mov['descripcion']
        fecha = mov['fecha']

        # Buscar coincidencia en cuotas
        cuota = facturas.filter(saldo_pendiente=monto).first()
        if cuota:
            cuota.estatus = 'cobrada'
            cuota.save()
            conciliados.append({
                'fecha': fecha,
                'monto': monto,
                'descripcion': descripcion,
                'tipo': 'Cuota'
            })
            continue

        # Buscar coincidencia en otros ingresos
        ingreso = otros_ingresos.filter(saldo_pendiente=monto).first()
        if ingreso:
            ingreso.estatus = 'cobrada'
            ingreso.save()
            conciliados.append({
                'fecha': fecha,
                'monto': monto,
                'descripcion': descripcion,
                'tipo': 'Otro ingreso'
            })
            continue

        # Buscar coincidencia en gastos
        gasto = gastos.filter(saldo_pendiente=monto).first()
        if gasto:
            gasto.estatus = 'pagado'
            gasto.save()
            conciliados.append({
                'fecha': fecha,
                'monto': monto,
                'descripcion': descripcion,
                'tipo': 'Gasto'
            })
            continue

        # Buscar coincidencia en fondeos de caja chica
        fondeo = fondeos.filter(saldo=monto).first()
        if fondeo:
            fondeo.numero_cheque = descripcion or fondeo.numero_cheque
            fondeo.save()
            conciliados.append({
                'fecha': fecha,
                'monto': monto,
                'descripcion': descripcion,
                'tipo': 'Fondeo caja chica'
            })
            continue

        # Si no se encontró coincidencia
        no_conciliados.append({
            'fecha': fecha,
            'monto': monto,
            'descripcion': descripcion
        })

    return {
        'conciliados': conciliados,
        'no_conciliados': no_conciliados,
        'fecha_min': fecha_min,
        'fecha_max': fecha_max,
    }

@login_required
def subir_estado_cuenta(request):
    empresa = request.user.perfilusuario.empresa
    if request.method == 'POST':
        archivo = request.FILES['archivo']
        # Guarda el archivo temporalmente
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            for chunk in archivo.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Conciliación mejorada: guarda lista de conciliados con tipo
        resultado = conciliar_estado_cuenta(tmp_path, empresa)
        conciliados = []
        no_conciliados = resultado.get('no_conciliados', [])
        fecha_min = resultado.get('fecha_min')
        fecha_max = resultado.get('fecha_max')

        # Vuelve a leer el archivo para obtener los conciliados con tipo
        from facturacion.models import Factura, FacturaOtrosIngresos
        from caja_chica.models import FondeoCajaChica
        from gastos.models import Gasto
        from datetime import datetime

        with open(tmp_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                fecha_str = row['fecha']
                try:
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                monto = float(row['monto'])
                descripcion = row.get('descripcion', '')

                # Buscar coincidencia en cuotas
                cuota = Factura.objects.filter(
                    empresa=empresa,
                    fecha_emision__gte=fecha_min,
                    fecha_emision__lte=fecha_max,
                    saldo_pendiente=monto,
                    estatus='cobrada'
                ).first()
                if cuota:
                    conciliados.append({
                        'fecha': fecha,
                        'monto': monto,
                        'descripcion': descripcion,
                        'tipo': 'Cuota'
                    })
                    continue

                # Buscar coincidencia en otros ingresos
                ingreso = FacturaOtrosIngresos.objects.filter(
                    empresa=empresa,
                    fecha_emision__gte=fecha_min,
                    fecha_emision__lte=fecha_max,
                    saldo_pendiente=monto,
                    estatus='cobrada'
                ).first()
                if ingreso:
                    conciliados.append({
                        'fecha': fecha,
                        'monto': monto,
                        'descripcion': descripcion,
                        'tipo': 'Otro ingreso'
                    })
                    continue

                # Buscar coincidencia en gastos
                gasto = Gasto.objects.filter(
                    empresa=empresa,
                    fecha__gte=fecha_min,
                    fecha__lte=fecha_max,
                    saldo_pendiente=monto,
                    estatus='pagado'
                ).first()
                if gasto:
                    conciliados.append({
                        'fecha': fecha,
                        'monto': monto,
                        'descripcion': descripcion,
                        'tipo': 'Gasto'
                    })
                    continue

                # Buscar coincidencia en fondeos de caja chica
                fondeo = FondeoCajaChica.objects.filter(
                    empresa=empresa,
                    fecha__gte=fecha_min,
                    fecha__lte=fecha_max,
                    saldo=monto
                ).first()
                if fondeo:
                    conciliados.append({
                        'fecha': fecha,
                        'monto': monto,
                        'descripcion': descripcion,
                        'tipo': 'Fondeo caja chica'
                    })
                    continue

        return render(request, 'conciliacion/resultado_conciliacion.html', {
            'conciliados': conciliados,
            'no_conciliados': no_conciliados,
            'fecha_min': fecha_min,
            'fecha_max': fecha_max,
        })

    return render(request, 'conciliacion/subir_estado_cuenta.html')


#Modulo de timbrado de facturas con FACTURAMA
FACTURAMA_USER = os.getenv("FACTURAMA_USER")
FACTURAMA_PASS = os.getenv("FACTURAMA_PASSWORD")


def timbrar_factura_facturama(datos_factura):
    url = 'https://apisandbox.facturama.mx/api-lite/3/cfdis'  # URL de sandbox desarrollo
    #url = 'https://api.facturama.mx/'  # URL de producción
    # print("JSON enviado a Facturama:", json.dumps(datos_factura, indent=2))
    # print("FACTURAMA_USER:", FACTURAMA_USER)
    # print("FACTURAMA_PASS:", FACTURAMA_PASS)
    response = requests.post(
        url,
        auth=(FACTURAMA_USER, FACTURAMA_PASS),
        headers={'Content-Type': 'application/json'},
        data=json.dumps(datos_factura)
    )
    # print("Status code:", response.status_code)
    # print("Response text:", response.text)
    try:
        return response.json()
    except Exception:
        return {'error': response.text}

def factura_a_json_facturama(factura, tax_object="02", payment_method="PUE", payment_form="99"):
    from decimal import Decimal, ROUND_HALF_UP
    from babel.dates import format_date
    import pytz

    monto = Decimal(factura.monto)
    tasa_iva = Decimal('0.16')
    divisor_iva = Decimal('1.16')

    empresa = factura.empresa
    cliente = factura.cliente

    tz_mx = pytz.timezone('America/Mexico_City')
    fecha_timbrado = timezone.now().astimezone(tz_mx).strftime("%Y-%m-%d %H:%M:%S")

    # --- ADAPTACIÓN PARA AMBOS TIPOS DE FACTURA ---
    # Para Factura normales
    if hasattr(factura, "tipo_cuota") and hasattr(factura, "fecha_vencimiento"):
        descripcion = "Aportación cuota " + str(getattr(factura, "tipo_cuota", "")) + " " + format_date(factura.fecha_vencimiento, "LLLL yyyy", locale="es")
    # Para FacturaOtrosIngresos
    elif hasattr(factura, "tipo_ingreso"):
        descripcion = "Otro ingreso: " + str(getattr(factura, "tipo_ingreso", "")) + (f" - {factura.observaciones}" if getattr(factura, "observaciones", "") else "")
    else:
        descripcion = factura.observaciones or "Concepto de factura"

    if tax_object == "01":
        # Sin objeto de impuesto: total y subtotal son iguales al monto
        subtotal = monto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        item_total = subtotal
        total = subtotal
    else:
        # Con objeto de impuesto: calcula subtotal y desglose de IVA
        subtotal = (monto / divisor_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        iva = (subtotal * tasa_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        item_total = (subtotal + iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = item_total

    item = {
        "ProductCode": "25173108",        
        "Description": descripcion,
        "UnitCode": "E48",
        "Quantity": 1.0,
        "UnitPrice": float(subtotal),
        "Subtotal": float(subtotal),
        "TaxObject": tax_object,
        "Total": float(item_total)
    }

    if tax_object == "02":
        item["Taxes"] = [{
            "Total": float(iva),
            "Name": "IVA",
            "Base": float(subtotal),
            "Rate": float(tasa_iva),
            "IsRetention": False
        }]

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
            "Name": empresa.nombre
        },
        "Receiver": {
            "Rfc": cliente.rfc,
            "CfdiUse": cliente.uso_cfdi,
            "Name": cliente.nombre,
            "FiscalRegime": cliente.regimen_fiscal,
            "TaxZipCode": cliente.codigo_postal,
        },
        "Items": [item],
        "Total": float(total)
    }
        

@login_required
def timbrar_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    empresa = factura.empresa
    
    # Solo permite timbrar si la empresa es PLUS
    if not empresa.es_plus:
        messages.error(request, "El timbrado solo está disponible en la versión PLUS del sistema.")
        return redirect('lista_facturas')

    if not request.user.is_superuser and factura.empresa != request.user.perfilusuario.empresa:
        messages.error(request, "No tienes permiso para timbrar esta factura.")
        return redirect('lista_facturas')

    if factura.uuid:
        messages.info(request, "La factura ya está timbrada.")
        return redirect('lista_facturas')

    if request.method == "POST":
        form = TimbrarFacturaForm(request.POST)
        if form.is_valid():
            tax_object = form.cleaned_data["tax_object"]
            payment_method = form.cleaned_data["payment_method"]
            payment_form = form.cleaned_data["payment_form"]
            datos_json = factura_a_json_facturama(factura, tax_object, payment_method, payment_form)
            resultado = timbrar_factura_facturama(datos_json)
            # print("Resultado de timbrado:", resultado)
            if 'error' in resultado:
                messages.error(request, f"Error al timbrar: {resultado['error']}")
            else:
                uuid = (
                    resultado.get('Uuid') or
                    resultado.get('Complement', {}).get('TaxStamp', {}).get('Uuid')
                )
                facturama_id = resultado.get('Id')
                if not uuid or not facturama_id:
                    messages.error(request, f"Error inesperado: {resultado}")
                else:
                    factura.uuid = uuid
                    factura.facturama_id = facturama_id
                    factura.save()
                    messages.success(request, "Factura " + factura.folio + " timbrada correctamente. Ahora puedes descargar el PDF y XML.")
            return redirect('lista_facturas')
    else:
        form = TimbrarFacturaForm()

    return render(request, "facturacion/timbrar_factura.html", {
                  "form": form, 
                   "factura": factura,
                   "url_cancelar":"lista_facturas"})

import requests
import io
import zipfile
from django.http import HttpResponse

@login_required
def descargar_factura_timbrada(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    if not factura.uuid:
        messages.error(request, "La factura no está timbrada.")
        return redirect('lista_facturas')

    uuid = factura.uuid
    usuario = os.getenv("FACTURAMA_USER")
    password = os.getenv("FACTURAMA_PASSWORD")

    # URLs para descargar XML y PDF
    xml_url = f"https://apisandbox.facturama.mx/api-lite/3/cfdis/{uuid}/xml"  #desarrollo
    pdf_url = f"https://apisandbox.facturama.mx/api-lite/3/cfdis/{uuid}/pdf"  #desarrollo
    
    #xml_url = f"https://api.facturama.mx/api-lite/3/cfdis/{uuid}/xml"  #producción
    #pdf_url = f"https://api.facturama.mx/api-lite/3/cfdis/{uuid}/pdf"  #producción


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
        messages.error(request, "No se pudo descargar el PDF ni el XML desde Facturama.")
        return redirect('lista_facturas')

    # Prepara ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        if xml_content:
            zip_file.writestr(f"factura_{factura.folio}.xml", xml_content)
        if pdf_content:
            zip_file.writestr(f"factura_{factura.folio}.pdf", pdf_content)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=factura_{factura.folio}.zip'
    return response


from .forms import CSDUploadForm
import base64

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
                url = "https://apisandbox.facturama.mx/api-lite/csds" #en desarrollo
                #url = "https://api.facturama.mx/api-lite/csds" # en producción
                data = {
                    "Rfc": rfc,
                    "Certificate": cert_b64,
                    "PrivateKey": key_b64,
                    "PrivateKeyPassword": key_password
                }
                response = requests.post(
                    url,
                    auth=(usuario, password),
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(data)
                )
                if response.status_code == 200:
                    mensaje = f"CSD cargado correctamente para la empresa {empresa.nombre}."
                    csds = obtener_csds_facturama(usuario, password)  # Actualiza lista
                else:
                    print("Status code:", response.status_code)
                    print("Response text:", response.text)
                    mensaje = f"Error al cargar CSD: {response.text}"
    else:
        form = CSDUploadForm()
    return render(request, "facturacion/subir_csd.html", {"form": form, "mensaje": mensaje, "csds": csds})


def obtener_csds_facturama(usuario, password):
    url = "https://apisandbox.facturama.mx/api-lite/csds"  # URL de sandbox desarrollo
    #url = "https://api.facturama.mx/api-lite/csds"  # URL de producción
    response = requests.get(url, auth=(usuario, password))
    if response.status_code == 200:
        return response.json()  # Lista de CSDs
    return []    


def consultar_cfdis_facturama(rfc_issuer=None, uuid=None, folio_start=None, folio_end=None, date_start=None, date_end=None, status="active", page=0):
    url = "https://apisandbox.facturama.mx/cfdi" # URL de sandbox desarrollo
    #url = "https://api.facturama.mx/cfdi"  # URL de producción
    params = {
        "type": "issuedLite",
        "status": status,
        "page": page
    }
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
        params["dateEnd"] = date_end      # formato: dd/mm/yyyy

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
            date_end=date_end
        )
        if not resultados:
            mensaje = "No se encontraron CFDIs con esos filtros o hubo un error en la consulta."

    return render(request, "facturacion/consulta_cfdis.html", {
        "empresas": empresas,
        "resultados": resultados,
        "mensaje": mensaje
    })


def descargar_cfdi_facturama(request, id):
    usuario = os.getenv("FACTURAMA_USER")
    password = os.getenv("FACTURAMA_PASSWORD")
    base_url = "https://apisandbox.facturama.mx/cfdi" # URL de sandbox desarrollo
    #base_url = "https://api.facturama.mx/cfdi"  # URL de producción

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
        messages.error(request, "No se pudo descargar el PDF ni el XML desde Facturama.")
        return redirect('consulta_cfdis_facturama')

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        if xml_content:
            zip_file.writestr(f"{id}.xml", xml_content)
        if pdf_content:
            zip_file.writestr(f"{id}.pdf", pdf_content)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=cfdi_{id}.zip'
    return response


# timbrar facturas de otros ingresos
@login_required
def timbrar_factura_otros_ingresos(request, pk):
    factura = get_object_or_404(FacturaOtrosIngresos, pk=pk)
    empresa = factura.empresa

    # Solo permite timbrar si la empresa es PLUS
    if not empresa.es_plus:
        messages.error(request, "El timbrado solo está disponible en la versión PLUS del sistema.")
        return redirect('lista_facturas_otros_ingresos')

    if factura.uuid:
        messages.info(request, "La factura ya está timbrada.")
        return redirect('lista_facturas_otros_ingresos')

    if request.method == "POST":
        form = TimbrarFacturaForm(request.POST)
        if form.is_valid():
            tax_object = form.cleaned_data["tax_object"]
            payment_method = form.cleaned_data["payment_method"]
            payment_form = form.cleaned_data["payment_form"]
            datos_json = factura_a_json_facturama(factura, tax_object, payment_method, payment_form)
            resultado = timbrar_factura_facturama(datos_json)
            print("Resultado de timbrado:", resultado)
            if 'error' in resultado:
                messages.error(request, f"Error al timbrar: {resultado['error']}")
            else:
                uuid = (
                    resultado.get('Uuid') or
                    resultado.get('Complement', {}).get('TaxStamp', {}).get('Uuid')
                )
                facturama_id = resultado.get('Id')
                if not uuid or not facturama_id:
                    messages.error(request, f"Error inesperado: {resultado}")
                else:
                    factura.uuid = uuid
                    factura.facturama_id = facturama_id
                    factura.save()
                    messages.success(request, "Factura " + factura.folio + " timbrada correctamente. Ahora puedes descargar el PDF y XML.")
            return redirect('lista_facturas_otros_ingresos')
    else:
        form = TimbrarFacturaForm()

    return render(request, "facturacion/timbrar_factura.html",
                   {"form": form, 
                    "factura": factura
                    , "url_cancelar":"lista_facturas_otros_ingresos"})



# Módulo de timbrado para visitantes
def visitante_timbrar_factura(request, pk):
    visitante_id = request.session.get("visitante_id")
    if not visitante_id:
        return redirect("visitante_login")
    visitante = VisitanteAcceso.objects.get(id=visitante_id)
    factura = get_object_or_404(Factura, pk=pk)
    # Verifica que la factura pertenezca a los locales/áreas del visitante
    if factura.local not in visitante.locales.all() and factura.area_comun not in visitante.areas.all():
        messages.error(request, "No tienes permiso para timbrar esta factura.")
        return redirect("visitante_consulta_facturas")

    empresa = factura.empresa
    if not empresa.es_plus:
        messages.error(request, "TIMBRADO de Facturas solo está disponible en la versión PLUS. Contacta al administrador del sistema.")
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
            datos_json = factura_a_json_facturama(factura, tax_object, payment_method, payment_form)
            resultado = timbrar_factura_facturama(datos_json)
            print("Resultado de timbrado:", resultado)
            if 'error' in resultado:
                messages.error(request, f"Error al timbrar: {resultado['error']}")
            else:
                uuid = (
                    resultado.get('Uuid') or
                    resultado.get('Complement', {}).get('TaxStamp', {}).get('Uuid')
                )
                facturama_id = resultado.get('Id')
                if not uuid or not facturama_id:
                    messages.error(request, f"Error inesperado: {resultado}")
                else:
                    factura.uuid = uuid
                    factura.facturama_id = facturama_id
                    factura.save()
                    messages.success(request, "Factura " + factura.folio + " timbrada correctamente. Ahora puedes descargar el PDF y XML.")
            return redirect("visitante_consulta_facturas")
    else:
        form = TimbrarFacturaForm()

    return render(request, "facturacion/timbrar_factura.html", {
        "form": form,
        "factura": factura,
        "url_cancelar": "visitante_consulta_facturas"
    })