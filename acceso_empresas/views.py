from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import UsuarioAcceso, AccesoEmpresa
from empresas.models import Empresa
import datetime
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


def portal_login(request):
    """Login exclusivo para usuarios de acceso"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Intentar encontrar usuario por email si no funciona por username
        if '@' in username:
            try:
                from django.contrib.auth.models import User
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('acceso_superuser_panel')
            elif hasattr(user, 'usuario_acceso'):
                if user.usuario_acceso.activo:
                    login(request, user)
                    return redirect('acceso_dashboard')
                else:
                    # ← En lugar de error, hacer login y mandar a pagar
                    login(request, user)
                    messages.warning(request,
                        "Tu cuenta está pendiente de pago. "
                        "Completa tu suscripción para acceder al portal."
                    )
                    return redirect('acceso_checkout')
            else:
                messages.error(request, "Este portal es exclusivo para empresas administradoras y comités.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'acceso_empresas/login.html')


def portal_registro(request):
    """Registro de nuevo usuario de acceso"""
    PLANES = [
        {
            'id': 'basico',
            'nombre': 'Básico',
            'precio': 299,
            'empresas': '1 empresa',
            'descripcion': 'Ideal para comités de un solo condominio',
        },
        {
            'id': 'profesional',
            'nombre': 'Profesional',
            'precio': 699,
            'empresas': 'hasta 3 empresas',
            'descripcion': 'Para administradoras con varios condominios',
        },
        {
            'id': 'enterprise',
            'nombre': 'Enterprise',
            'precio': 1499,
            'empresas': 'Ilimitadas',
            'descripcion': 'Para grandes empresas administradoras',
        },
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

        # Validaciones
        if not all([nombre, email, password, tipo, nombre_organizacion]):
            messages.error(request, "Todos los campos marcados con * son obligatorios.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        if User.objects.filter(email=email).exists():
            messages.error(request, "Ya existe una cuenta con ese correo electrónico.")
            return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})

        # Crear usuario
        username = email.split('@')[0]
        # Asegurar username único
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellido,
        )

        UsuarioAcceso.objects.create(
            usuario=user,
            tipo=tipo,
            plan=plan,
            nombre_organizacion=nombre_organizacion,
            telefono=telefono,
            activo=False,  # Se activa al pagar
        )

        # Login automático para que el template de pago pueda mostrar el botón
        login(request, user)

        messages.success(request,
            "Cuenta creada correctamente. "
            "Completa el pago de tu suscripción para activar tu acceso."
        )
        return redirect('acceso_checkout')  # ← directo al checkout, no a pago_pendiente

    return render(request, 'acceso_empresas/registro.html', {'planes': PLANES})


def portal_logout(request):
    logout(request)
    return redirect('acceso_login')


def pago_pendiente(request):
    return render(request, 'acceso_empresas/pago_pendiente.html')


def requiere_acceso(f):
    """Decorator para vistas del portal de acceso"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('acceso_login')
        if not hasattr(request.user, 'usuario_acceso'):
            if request.user.is_superuser:
                return f(request, *args, **kwargs)
            return redirect('acceso_login')
        if not request.user.usuario_acceso.activo:
            messages.error(request, "Tu suscripción no está activa.")
            return redirect('acceso_pago_pendiente')
        return f(request, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@requiere_acceso
def dashboard(request):
    """Dashboard principal del usuario de acceso"""
    if request.user.is_superuser:
        return redirect('acceso_superuser_panel')

    ua = request.user.usuario_acceso
    accesos = AccesoEmpresa.objects.filter(
        usuario_acceso=ua
    ).select_related('empresa').order_by('estado', 'empresa__nombre')

    # Empresa activa (desde sesión)
    empresa_activa_id = request.session.get('acceso_empresa_activa_id')
    empresa_activa = None
    acceso_activo = None
    if empresa_activa_id:
        acceso_activo = accesos.filter(
            empresa_id=empresa_activa_id, aprobado=True, activo=True
        ).first()
        if acceso_activo:
            empresa_activa = acceso_activo.empresa

    # Si no hay empresa activa, usar la primera aprobada
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
    """Cambiar la empresa activa en sesión"""
    ua = request.user.usuario_acceso
    acceso = get_object_or_404(AccesoEmpresa,
        usuario_acceso=ua, empresa_id=empresa_id, aprobado=True, activo=True
    )
    request.session['acceso_empresa_activa_id'] = empresa_id
    messages.success(request, f"Ahora viendo: {acceso.empresa.nombre}")
    return redirect('acceso_dashboard')


@requiere_acceso
def solicitar_acceso_empresa(request):
    """Solicitar acceso a una empresa"""
    ua = request.user.usuario_acceso

    if not ua.puede_agregar_empresa:
        messages.error(request,
            f"Tu plan {ua.get_plan_display()} permite máximo {ua.limite_empresas} empresa(s). "
            "Actualiza tu plan para agregar más."
        )
        return redirect('acceso_dashboard')

    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        empresa = get_object_or_404(Empresa, pk=empresa_id)

        if AccesoEmpresa.objects.filter(usuario_acceso=ua, empresa=empresa).exists():
            messages.warning(request, "Ya tienes una solicitud para esta empresa.")
            return redirect('acceso_dashboard')

        AccesoEmpresa.objects.create(
            usuario_acceso=ua,
            empresa=empresa,
            estado='pendiente',
            aprobado=False,
        )
        messages.success(request,
            f"Solicitud enviada para '{empresa.nombre}'. "
            "El administrador revisará tu solicitud."
        )
        return redirect('acceso_dashboard')

    # Buscar empresas
    query = request.GET.get('q', '')
    empresas = []
    if query and len(query) >= 3:
        empresas_ids_ya_solicitadas = ua.accesos_empresas.values_list('empresa_id', flat=True)
        empresas = Empresa.objects.filter(
            nombre__icontains=query
        ).exclude(id__in=empresas_ids_ya_solicitadas)[:10]

    return render(request, 'acceso_empresas/solicitar_empresa.html', {
        'empresas': empresas,
        'query': query,
        'ua': ua,
    })


# ============ VISTAS DE REPORTES ============

@requiere_acceso
def reporte_estado_resultados(request):
    acceso_activo = _get_acceso_activo(request)
    if not acceso_activo or not acceso_activo.ver_estado_resultados:
        messages.error(request, "No tienes acceso a este reporte.")
        return redirect('acceso_dashboard')

    request.session['empresa_id'] = acceso_activo.empresa.id
    request.is_portal_acceso = True  # ← marca el request
    request.acceso_activo = acceso_activo
    request.empresa_activa_portal = acceso_activo.empresa

    from informes_financieros.views import estado_resultados
    return estado_resultados(request)


#dashboard_saldos
@requiere_acceso
def reporte_cobranza(request):
    acceso_activo = _get_acceso_activo(request)
    if not acceso_activo or not acceso_activo.ver_cobranza:
        messages.error(request, "No tienes acceso a este reporte.")
        return redirect('acceso_dashboard')

    request.session['empresa_id'] = acceso_activo.empresa.id
    request.is_portal_acceso = True  # ← esto controla el navbar
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
    request.is_portal_acceso = True  # ← esto controla el navbar
    request.acceso_activo = acceso_activo
    request.empresa_activa_portal = acceso_activo.empresa

    from informes_financieros.views import reporte_ingresos_vs_gastos  # o la vista que uses para gastos
    return reporte_ingresos_vs_gastos(request)


def _get_acceso_activo(request):
    """Helper: obtener el acceso activo del usuario"""
    if not hasattr(request.user, 'usuario_acceso'):
        return None
    ua = request.user.usuario_acceso
    empresa_id = request.session.get('acceso_empresa_activa_id')
    if not empresa_id:
        return None
    return AccesoEmpresa.objects.filter(
        usuario_acceso=ua,
        empresa_id=empresa_id,
        aprobado=True,
        activo=True,
    ).first()


# ============ PANEL SUPERUSUARIO ============

@login_required(login_url='/portal/login/')
def superuser_panel(request):
    if not request.user.is_superuser:
        return redirect('acceso_login')

    solicitudes_pendientes = AccesoEmpresa.objects.filter(
        estado='pendiente'
    ).select_related('usuario_acceso__usuario', 'empresa').order_by('-fecha_solicitud')

    todos_usuarios = UsuarioAcceso.objects.select_related(
        'usuario'
    ).prefetch_related('accesos_empresas__empresa').order_by('-fecha_registro')

    return render(request, 'acceso_empresas/superuser_panel.html', {
        'solicitudes_pendientes': solicitudes_pendientes,
        'todos_usuarios': todos_usuarios,
    })


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
            # Permisos configurados por el superusuario
            acceso.ver_dashboard = request.POST.get('ver_dashboard') == 'on'
            acceso.ver_estado_resultados = request.POST.get('ver_estado_resultados') == 'on'
            acceso.ver_cobranza = request.POST.get('ver_cobranza') == 'on'
            acceso.ver_gastos = request.POST.get('ver_gastos') == 'on'
            acceso.save()

            # Activar usuario si no estaba activo
            ua = acceso.usuario_acceso
            if not ua.activo:
                ua.activo = True
                ua.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=30)
                ua.save()

            messages.success(request,
                f"Acceso aprobado para {ua} a {acceso.empresa.nombre}."
            )

        elif accion == 'rechazar':
            acceso.estado = 'rechazado'
            acceso.aprobado = False
            acceso.save()
            messages.warning(request, "Solicitud rechazada.")

        return redirect('acceso_superuser_panel')

    return render(request, 'acceso_empresas/aprobar_acceso.html', {'acceso': acceso})


@login_required(login_url='/portal/login/')
def editar_permisos(request, acceso_id):
    """Editar permisos de un acceso ya aprobado"""
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


# ===========PANEL STRIPE CHECKOUT=========== #

@login_required(login_url='/portal/login/')
def checkout_suscripcion(request):
    """Redirige al usuario a Stripe Checkout para pagar su plan"""
    if not hasattr(request.user, 'usuario_acceso'):
        return redirect('acceso_login')

    ua = request.user.usuario_acceso
    stripe.api_key = settings.STRIPE_SECRET_KEY

    price_id = settings.STRIPE_PORTAL_PRICES.get(ua.plan)
    if not price_id:
        messages.error(request, "Plan no válido.")
        return redirect('acceso_pago_pendiente')

    try:
        # Crear o recuperar customer en Stripe
        if ua.stripe_customer_id:
            customer_id = ua.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name() or request.user.username,
                metadata={'usuario_acceso_id': ua.id, 'plan': ua.plan}
            )
            ua.stripe_customer_id = customer.id
            ua.save()
            customer_id = customer.id

        # Crear sesión de checkout
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

    except stripe.error.StripeError as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('acceso_pago_pendiente')


def pago_exitoso(request):
    """Página de confirmación después del pago"""
    return render(request, 'acceso_empresas/pago_exitoso.html')


@csrf_exempt
def stripe_webhook_portal(request):
    """Webhook de Stripe para el portal de acceso"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
   #webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    webhook_secret = settings.STRIPE_PORTAL_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        usuario_acceso_id = session.get('metadata', {}).get('usuario_acceso_id')
        subscription_id = session.get('subscription')

        if usuario_acceso_id:
            try:
                ua = UsuarioAcceso.objects.get(pk=usuario_acceso_id)
                ua.activo = True
                ua.stripe_subscription_id = subscription_id
                ua.fecha_vencimiento = datetime.date.today() + datetime.timedelta(days=30)
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
        subscription_id = event['data']['object'].get('id') or event['data']['object'].get('subscription')
        if subscription_id:
            try:
                ua = UsuarioAcceso.objects.get(stripe_subscription_id=subscription_id)
                ua.activo = False
                ua.save()
            except UsuarioAcceso.DoesNotExist:
                pass

    return HttpResponse(status=200)    