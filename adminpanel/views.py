from django.contrib import messages
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render
from principal.models import VisitanteAcceso
from django.shortcuts import redirect, get_object_or_404
from django.core.mail import send_mail

@staff_member_required
def lista_usuarios_normales(request):
    usuarios = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, "adminpanel/lista_usuarios.html", {"usuarios": usuarios})

@staff_member_required
def lista_usuarios_visitantes(request):
    visitantes = VisitanteAcceso.objects.all().order_by('-id')
    return render(request, "adminpanel/lista_visitantes.html", {"visitantes": visitantes})

@staff_member_required
def toggle_activo_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.activo = not visitante.activo
    visitante.save()
    estado = "activado" if visitante.activo else "desactivado"
    messages.success(request, f"El visitante {visitante.username} ha sido {estado}.")

    # Enviar correo solo si se activó
    if visitante.activo:
        mensaje = (
            f"Hola {visitante.nombre},\n\n"
            "Tu cuenta ha sido activada por el sistema GESAC. Ya puedes ingresar: https://adminsoftheron.onrender.com/visitante/login/ \n\n"
            "Atentamente,\n"
            "El equipo de SoftHeron. \n\n" 
            "Gracias por utilizar nuestro sistema. Visita nuestra página web: \n"
            "https://paginaweb-ro9v.onrender.com \n"
            
        )
        send_mail(
            'Tu cuenta ha sido activada',
            mensaje,
            settings.EMAIL_HOST_USER, 
            [visitante.email],
            fail_silently=True,
        )
    return redirect('lista_usuarios_visitantes')

@staff_member_required
def toggle_reporte_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.acceso_api_reporte = not visitante.acceso_api_reporte
    visitante.save()
    return redirect('lista_usuarios_visitantes')