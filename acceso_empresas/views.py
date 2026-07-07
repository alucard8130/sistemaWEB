from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import UsuarioAcceso, AccesoEmpresa
from empresas.models import Empresa
import datetime
import secrets
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta


# def _get_usuario_acceso(request):
#     """Obtiene el UsuarioAcceso desde la sesión"""
#     ua_id = request.session.get('ua_id')
#     if not ua_id:
#         return None
#     try:
#         return UsuarioAcceso.objects.get(pk=ua_id, activo=True)
#     except UsuarioAcceso.DoesNotExist:
#         return None


def requiere_acceso(f):
    """Decorator para vistas del portal — usa sesión propia sin User de Django"""
    def wrapper(request, *args, **kwargs):
        ua_id = request.session.get('ua_id')
        if not ua_id:
            return redirect('acceso_login')
        try:
            ua = UsuarioAcceso.objects.get(pk=ua_id)
            if not ua.activo:
                return redirect('acceso_checkout')
            request.ua = ua
        except UsuarioAcceso.DoesNotExist:
            return redirect('acceso_login')
        return f(request, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def portal_login(request):
    if request.method == 'POST':
        email_o_user = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Intentar como superusuario de Django (username o email)
        django_user = authenticate(request, username=email_o_user, password=password)
        if not django_user and '@' in email_o_user:
            # Intentar por email
            try:
                u = User.objects.get(email=email_o_user)
                django_user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if django_user and django_user.is_superuser:
            login(request, django_user)
            return redirect('acceso_superuser_panel')

        # Intentar como UsuarioAcceso del portal (solo por email)
        if '@' in email_o_user:
            try:
                ua = UsuarioAcceso.objects.get(email=email_o_user)
                if ua.check_password(password):
                    if not ua.activo:
                        request.session['ua_id'] = ua.id
                        messages.warning(request, "Tu cuenta está pendiente de pago.")
                        return redirect('acceso_checkout')
                    request.session['ua_id'] = ua.id
                    return redirect('acceso_dashboard')
                else:
                    messages.error(request, "Email o contraseña incorrectos.")
            except UsuarioAcceso.DoesNotExist:
                messages.error(request, "Email o contraseña incorrectos.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'acceso_empresas/login.html')


def portal_logout(request):
    request.session.flush()
    if request.user.is_authenticated:
        logout(request)
    return redirect('acceso_login')


def portal_registro(request):
    PLANES = [
        {'id': 'basico', 'nombre': 'Básico', 'precio': 299,
         'empresas': '1 condominio', 'descripcion': 'Ideal para comités de un solo condominio'},
        {'id': 'profesional', 'nombre': 'Profesional', 'precio': 499,
         'empresas': 'hasta 3 condominios', 'descripcion': 'Para administradoras con varios condominios'},
        {'id': 'enterprise', 'nombre': 'Enterprise', 'precio': 999,
         'empresas': 'Ilimitados', 'descripcion': 'Para grandes empresas administradoras'},
    ]

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        tipo = request.POST.get('tipo', '')
        plan = request.POST.get('plan', 'basico')
        nombre_organizacion = request.POST.get('nombre_organizacion', '').strip()
        telefono = request.POST.get('telefono', '').strip()

        if not all([nombre, email, password, tipo, nombre_organizacion]):
            messages.error(request, "Todos los campos marcados con * son obligatorios.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        if UsuarioAcceso.objects.filter(email=email).exists():
            messages.error(request, "Ya existe una cuenta con ese correo electrónico.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        # Crear UsuarioAcceso sin User de Django
        ua = UsuarioAcceso(
            nombre=f"{nombre} {apellido}".strip(),
            email=email,
            telefono=telefono,
            nombre_organizacion=nombre_organizacion,
            tipo=tipo,
            plan=plan,
            activo=False,
        )
        ua.set_password(password)
        ua.save()

        # Guardar en sesión
        request.session['ua_id'] = ua.id

        messages.success(request, "Cuenta creada. Completa el pago para activar tu acceso.")
        return redirect('acceso_checkout')

    return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})


def pago_pendiente(request):
    return render(request, 'acceso_empresas/pago_pendiente.html')


def pago_exitoso(request):
    return render(request, 'acceso_empresas/pago_exitoso.html')


def checkout_suscripcion(request):
    import stripe
    from django.conf import settings

    ua_id = request.session.get('ua_id')
    if not ua_id:
        return redirect('acceso_login')

    try:
        ua = UsuarioAcceso.objects.get(pk=ua_id)
    except UsuarioAcceso.DoesNotExist:
        return redirect('acceso_login')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    price_id = settings.STRIPE_PORTAL_PRICES.get(ua.plan)

    if not price_id:
        messages.error(request, "Plan no válido.")
        return redirect('acceso_pago_pendiente')

    try:
        if ua.stripe_customer_id:
            customer_id = ua.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=ua.email,
                name=ua.nombre,
                metadata={'usuario_acceso_id': ua.id, 'plan': ua.plan}
            )
            ua.stripe_customer_id = customer.id
            ua.save()
            customer_id = customer.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=request.build_absolute_uri('/portal/pago-exitoso/'),
            cancel_url=request.build_absolute_uri('/portal/pago-pendiente/'),
            metadata={'usuario_acceso_id': ua.id, 'plan': ua.plan},
        )
        return redirect(session.url, permanent=False)

    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('acceso_pago_pendiente')


@requiere_acceso
def dashboard(request):
    ua = request.ua
    accesos = AccesoEmpresa.objects.filter(
        usuario_acceso=ua
    ).select_related('empresa').order_by('estado', 'empresa__nombre')

    empresa_activa_id = request.session.get('acceso_empresa_activa_id')
    empresa_activa = None
    acceso_activo = None
    if empresa_activa_id:
        acceso_activo = accesos.filter(
            empresa_id=empresa_activa_id, aprobado=True, activo=True
        ).first()
        if acceso_activo:
            empresa_activa = acceso_activo.empresa

    if not empresa_activa:
        primer_acceso = accesos.filter(aprobado=True, activo=True).first()
        if primer_acceso:
            empresa_activa = primer_acceso.empresa
            acceso_activo = primer_acceso
            request.session['acceso_empresa_activa_id'] = empresa_activa.id

    return render(request, 'acceso_empresas/dashboard.html', {
        'ua': ua,
        'accesos': accesos,
        'empresa_activa': empresa_activa,
        'acceso_activo': acceso_activo,
    })


@requiere_acceso
def cambiar_empresa_activa(request, empresa_id):
    ua = request.ua
    acceso = get_object_or_404(AccesoEmpresa,
        usuario_acceso=ua, empresa_id=empresa_id, aprobado=True, activo=True)
    request.session['acceso_empresa_activa_id'] = empresa_id
    messages.success(request, f"Ahora viendo: {acceso.empresa.nombre}")
    return redirect('acceso_dashboard')


@requiere_acceso
def solicitar_acceso_empresa(request):
    ua = request.ua
    if not ua.puede_agregar_empresa:
        messages.error(request, f"Tu plan permite máximo {ua.limite_empresas} empresa(s).")
        return redirect('acceso_dashboard')

    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        empresa = get_object_or_404(Empresa, pk=empresa_id)
        if AccesoEmpresa.objects.filter(usuario_acceso=ua, empresa=empresa).exists():
            messages.warning(request, "Ya tienes una solicitud para esta empresa.")
            return redirect('acceso_dashboard')
        AccesoEmpresa.objects.create(usuario_acceso=ua, empresa=empresa, estado='pendiente')
        messages.success(request, f"Solicitud enviada para '{empresa.nombre}'.")
        return redirect('acceso_dashboard')

    query = request.GET.get('q', '')
    empresas = []
    if query and len(query) >= 3:
        ids_ya = ua.accesos_empresas.values_list('empresa_id', flat=True)
        empresas = Empresa.objects.filter(nombre__icontains=query).exclude(id__in=ids_ya)[:10]

    return render(request, 'acceso_empresas/solicitar_empresa.html', {
        'empresas': empresas, 'query': query, 'ua': ua,
    })


def _get_acceso_activo(request):
    ua_id = request.session.get('ua_id')
    empresa_id = request.session.get('acceso_empresa_activa_id')
    if not ua_id or not empresa_id:
        return None
    try:
        ua = UsuarioAcceso.objects.get(pk=ua_id, activo=True)
        return AccesoEmpresa.objects.filter(
            usuario_acceso=ua,
            empresa_id=empresa_id,
            aprobado=True,
            activo=True,
        ).first()
    except UsuarioAcceso.DoesNotExist:
        return None


@requiere_acceso
def reporte_estado_resultados(request):
    acceso_activo = _get_acceso_activo(request)
    if not acceso_activo or not acceso_activo.ver_estado_resultados:
        messages.error(request, "No tienes acceso a este reporte.")
        return redirect('acceso_dashboard')
    request.session['empresa_id'] = acceso_activo.empresa.id
    request.is_portal_acceso = True
    request.acceso_activo = acceso_activo
    request.empresa_activa_portal = acceso_activo.empresa
    from informes_financieros.views import estado_resultados
    return estado_resultados(request)


@requiere_acceso
def reporte_cobranza(request):
    acceso_activo = _get_acceso_activo(request)
    if not acceso_activo or not acceso_activo.ver_cobranza:
        messages.error(request, "No tienes acceso a este reporte.")
        return redirect('acceso_dashboard')
    request.session['empresa_id'] = acceso_activo.empresa.id
    request.is_portal_acceso = True
    request.acceso_activo = acceso_activo
    request.empresa_activa_portal = acceso_activo.empresa
    from facturacion.views import dashboard_saldos
    return dashboard_saldos(request)


@requiere_acceso
def reporte_gastos(request):
    acceso_activo = _get_acceso_activo(request)
    if not acceso_activo or not acceso_activo.ver_gastos:
        messages.error(request, "No tienes acceso a este reporte.")
        return redirect('acceso_dashboard')
    request.session['empresa_id'] = acceso_activo.empresa.id
    request.is_portal_acceso = True
    request.acceso_activo = acceso_activo
    request.empresa_activa_portal = acceso_activo.empresa
    from informes_financieros.views import reporte_ingresos_vs_gastos
    return reporte_ingresos_vs_gastos(request)

@requiere_acceso
def upgrade_plan(request, nuevo_plan):
    import stripe
    from django.conf import settings

    ua = request.ua
    planes_validos = {
        'basico': ['profesional', 'enterprise'],
        'profesional': ['enterprise'],
    }

    if nuevo_plan not in planes_validos.get(ua.plan, []):
        messages.error(request, "Plan no válido.")
        return redirect('acceso_dashboard')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    price_id = settings.STRIPE_PORTAL_PRICES.get(nuevo_plan)

    try:
        session = stripe.checkout.Session.create(
            customer=ua.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=request.build_absolute_uri('/portal/pago-exitoso/'),
            cancel_url=request.build_absolute_uri('/portal/'),
            metadata={'usuario_acceso_id': ua.id, 'plan': nuevo_plan},
        )
        return redirect(session.url, permanent=False)
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('acceso_dashboard')
    
# ============ PANEL SUPERUSUARIO ============

@login_required(login_url='/portal/login/')
def superuser_panel(request):
    if not request.user.is_superuser:
        return redirect('acceso_login')

    solicitudes_pendientes = AccesoEmpresa.objects.filter(
        estado='pendiente'
    ).select_related('usuario_acceso', 'empresa').order_by('-fecha_solicitud')

    todos_usuarios = UsuarioAcceso.objects.prefetch_related(
        'accesos_empresas__empresa'
    ).order_by('-fecha_registro')

    return render(request, 'acceso_empresas/superuser_panel.html', {
        'solicitudes_pendientes': solicitudes_pendientes,
        'todos_usuarios': todos_usuarios,
    })


@login_required(login_url='/portal/login/')
def activar_usuario(request, ua_pk):
    if not request.user.is_superuser:
        return redirect('acceso_login')
    ua = get_object_or_404(UsuarioAcceso, pk=ua_pk)
    if request.method == 'POST':
        ua.activo = True
        ua.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=30)
        ua.save()
        messages.success(request, f"Usuario {ua} activado correctamente.")
    return redirect('acceso_superuser_panel')


@login_required(login_url='/portal/login/')
def aprobar_acceso(request, acceso_id):
    if not request.user.is_superuser:
        return redirect('acceso_login')

    acceso = get_object_or_404(AccesoEmpresa, pk=acceso_id)

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'aprobar':
            acceso.estado = 'aprobado'
            acceso.aprobado = True
            acceso.aprobado_por = request.user
            acceso.fecha_aprobacion = timezone.now()
            acceso.ver_dashboard = request.POST.get('ver_dashboard') == 'on'
            acceso.ver_estado_resultados = request.POST.get('ver_estado_resultados') == 'on'
            acceso.ver_cobranza = request.POST.get('ver_cobranza') == 'on'
            acceso.ver_gastos = request.POST.get('ver_gastos') == 'on'
            acceso.save()

            ua = acceso.usuario_acceso
            if not ua.activo:
                ua.activo = True
                ua.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=30)
                ua.save()

            messages.success(request, f"Acceso aprobado para {ua} a {acceso.empresa.nombre}.")

        elif accion == 'rechazar':
            acceso.estado = 'rechazado'
            acceso.aprobado = False
            acceso.save()
            messages.warning(request, "Solicitud rechazada.")

        return redirect('acceso_superuser_panel')

    return render(request, 'acceso_empresas/aprobar_acceso.html', {'acceso': acceso})


@login_required(login_url='/portal/login/')
def editar_permisos(request, acceso_id):
    if not request.user.is_superuser:
        return redirect('acceso_login')

    acceso = get_object_or_404(AccesoEmpresa, pk=acceso_id)
    if request.method == 'POST':
        acceso.ver_dashboard = request.POST.get('ver_dashboard') == 'on'
        acceso.ver_estado_resultados = request.POST.get('ver_estado_resultados') == 'on'
        acceso.ver_cobranza = request.POST.get('ver_cobranza') == 'on'
        acceso.ver_gastos = request.POST.get('ver_gastos') == 'on'
        acceso.activo = request.POST.get('activo') == 'on'
        acceso.save()
        messages.success(request, "Permisos actualizados correctamente.")
        return redirect('acceso_superuser_panel')

    return render(request, 'acceso_empresas/editar_permisos.html', {'acceso': acceso})


@csrf_exempt
def stripe_webhook_portal(request):
    import stripe
    from django.conf import settings

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_PORTAL_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        usuario_acceso_id = session.get('metadata', {}).get('usuario_acceso_id')
        nuevo_plan = session.get('metadata', {}).get('plan')
        subscription_id = session.get('subscription')
        if usuario_acceso_id:
            try:
                ua = UsuarioAcceso.objects.get(pk=usuario_acceso_id)
                ua.activo = True
                ua.stripe_subscription_id = subscription_id
                ua.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=30)
                if nuevo_plan in ['basico', 'profesional', 'enterprise']:
                    ua.plan = nuevo_plan
                ua.save()
            except UsuarioAcceso.DoesNotExist:
                pass

    elif event['type'] == 'invoice.payment_succeeded':
        subscription_id = event['data']['object'].get('subscription')
        if subscription_id:
            try:
                ua = UsuarioAcceso.objects.get(stripe_subscription_id=subscription_id)
                ua.activo = True
                ua.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=30)
                ua.save()
            except UsuarioAcceso.DoesNotExist:
                pass

    elif event['type'] in ['customer.subscription.deleted', 'invoice.payment_failed']:
        subscription_id = event['data']['object'].get('id') or \
                         event['data']['object'].get('subscription')
        if subscription_id:
            try:
                ua = UsuarioAcceso.objects.get(stripe_subscription_id=subscription_id)
                ua.activo = False
                ua.save()
            except UsuarioAcceso.DoesNotExist:
                pass

    return HttpResponse(status=200)


def cerrar_wizard(request):
    request.session['wizard_cerrado'] = True
    return redirect('pantalla_inicio')  



def password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            ua = UsuarioAcceso.objects.get(email=email)
            # Generar token único
            token = secrets.token_urlsafe(32)
            ua.reset_token = token
            ua.reset_token_expira = timezone.now() + timedelta(hours=24)
            ua.save()

            # Construir URL de reset
            reset_url = request.build_absolute_uri(
                f'/portal/password/reset/{token}/'
            )

            # Enviar email
            send_mail(
                subject='Restablecer contraseña — GESAC Portal',
                message=f"""Hola {ua.nombre},

Recibimos una solicitud para restablecer la contraseña de tu cuenta en GESAC Portal.

Haz clic en el siguiente enlace para crear una nueva contraseña:

{reset_url}

Este enlace expirará en 24 horas.

Si no solicitaste este cambio, puedes ignorar este mensaje.

— Equipo GESAC""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ua.email],
                fail_silently=True,
            )
        except UsuarioAcceso.DoesNotExist:
            pass  # No revelar si el email existe o no

        # Siempre redirigir al done para no revelar si existe el email
        return redirect('acceso_password_reset_done')

    return render(request, 'acceso_empresas/password_reset.html')


def password_reset_done(request):
    return render(request, 'acceso_empresas/password_reset_done.html')


def password_reset_confirm(request, token):
    try:
        ua = UsuarioAcceso.objects.get(
            reset_token=token,
            reset_token_expira__gt=timezone.now()
        )
    except UsuarioAcceso.DoesNotExist:
        ua = None

    if request.method == 'POST' and ua:
        password1 = request.POST.get('new_password1', '')
        password2 = request.POST.get('new_password2', '')

        if len(password1) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
        elif password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
        else:
            ua.set_password(password1)
            ua.reset_token = None
            ua.reset_token_expira = None
            ua.save()
            return redirect('acceso_password_reset_complete')

    return render(request, 'acceso_empresas/password_reset_confirm.html', {
        'validlink': ua is not None,
    })


def password_reset_complete(request):
    return render(request, 'acceso_empresas/password_reset_complete.html')
