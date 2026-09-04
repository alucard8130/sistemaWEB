
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from principal.models import PerfilUsuario
from usuarios_extra.models import InvitacionUsuarioEmpresa, limite_usuarios_empresa


@login_required
def invitar_usuario_empresa(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')
 
    empresa = perfil.empresa
    limite = limite_usuarios_empresa(empresa)
    # NUEVO -- excluye contadores del conteo: son un tipo de acceso
    # distinto (es_contador=True), no cuentan contra el límite de
    # usuarios operativos incluidos en el plan.
    usuarios_actuales_count = PerfilUsuario.objects.filter(empresa=empresa).exclude(es_contador=True).count()
    invitaciones_pendientes = InvitacionUsuarioEmpresa.objects.filter(empresa=empresa, estado='pendiente')
 
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Captura un correo válido.")
            return redirect('invitar_usuario_empresa')
 
        ocupados = usuarios_actuales_count + invitaciones_pendientes.count()
        if ocupados >= limite:
            messages.error(
                request,
                f"Tu plan permite hasta {limite} usuario(s) en total -- ya alcanzaste el límite."
            )
            return redirect('invitar_usuario_empresa')
 
        if User.objects.filter(email=email, perfilusuario__empresa=empresa).exists():
            messages.error(request, "Ese correo ya tiene acceso a tu empresa.")
            return redirect('invitar_usuario_empresa')
 
        if InvitacionUsuarioEmpresa.objects.filter(empresa=empresa, email=email, estado='pendiente').exists():
            messages.error(request, "Ya hay una invitación pendiente para ese correo.")
            return redirect('invitar_usuario_empresa')
 
        token = secrets.token_urlsafe(32)
        InvitacionUsuarioEmpresa.objects.create(
            empresa=empresa, email=email, token=token, invitado_por=request.user,
        )
 
        link = request.build_absolute_uri(reverse('aceptar_invitacion_usuario', args=[token]))
        send_mail(
            "Te invitaron a GESAC",
            f"Te invitaron a colaborar en {empresa.nombre} dentro de GESAC.\n\n"
            f"Da clic en este enlace para crear tu cuenta:\n{link}",
            None, [email], fail_silently=True,
        )
        messages.success(request, f"Invitación enviada a {email}.")
        return redirect('invitar_usuario_empresa')
 
    return render(request, 'usuarios_extra/invitar_usuario.html', {
        'empresa': empresa,
        'limite': limite,
        'usuarios_actuales_count': usuarios_actuales_count,
        'invitaciones_pendientes': invitaciones_pendientes,
        'usuarios': PerfilUsuario.objects.filter(empresa=empresa).exclude(es_contador=True).select_related('usuario'),
    })



def aceptar_invitacion_usuario(request, token):
    invitacion = get_object_or_404(InvitacionUsuarioEmpresa, token=token, estado='pendiente')
 
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
 
        if not nombre or not username or not password:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('aceptar_invitacion_usuario', token=token)
 
        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return redirect('aceptar_invitacion_usuario', token=token)
 
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ese nombre de usuario ya existe -- elige otro.")
            return redirect('aceptar_invitacion_usuario', token=token)
 
        empresa = invitacion.empresa
 
        limite = limite_usuarios_empresa(empresa)
        # NUEVO -- misma exclusión de contadores que en invitar_usuario_empresa
        usuarios_actuales_count = PerfilUsuario.objects.filter(empresa=empresa).exclude(es_contador=True).count()
        if usuarios_actuales_count >= limite:
            messages.error(request, "El límite de usuarios de esta empresa ya se alcanzó.")
            invitacion.estado = 'cancelada'
            invitacion.save(update_fields=['estado'])
            return redirect('login')
 
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=invitacion.email, password=password, first_name=nombre,
            )
 
            perfil_existente = PerfilUsuario.objects.filter(empresa=empresa).exclude(es_contador=True).first()
 
            # NUEVO -- si ya existe un PerfilUsuario para este usuario
            # (por ejemplo, creado automáticamente por una señal al
            # crear el User), lo actualiza en vez de intentar crear
            # uno nuevo y chocar con la restricción de unicidad.
            PerfilUsuario.objects.update_or_create(
                usuario=user,
                defaults={
                    'empresa': empresa,
                    'tipo_usuario': perfil_existente.tipo_usuario if perfil_existente else 'demo',
                    'fecha_vencimiento': perfil_existente.fecha_vencimiento if perfil_existente else None,
                },
            )
 
            invitacion.estado = 'aceptada'
            invitacion.fecha_aceptada = timezone.now()
            invitacion.save(update_fields=['estado', 'fecha_aceptada'])
 
        messages.success(request, "Tu cuenta fue creada correctamente -- ya puedes iniciar sesión.")
        return redirect('login')
 
    return render(request, 'usuarios_extra/aceptar_invitacion.html', {'invitacion': invitacion})


