from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from notificaciones_sistema.models import NotificacionLeida, NotificacionSistema


@login_required
def crear_notificacion_sistema(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para ver esta pantalla.")
        return redirect('dashboard_inicio')

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        titulo = request.POST.get('titulo', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        dispara_tour = request.POST.get('dispara_tour') == 'on'  # NUEVO

        if tipo not in dict(NotificacionSistema.TIPO_CHOICES):
            messages.error(request, "Selecciona un tipo válido.")
            return redirect('crear_notificacion_sistema')
        if not titulo or not mensaje:
            messages.error(request, "El título y el mensaje son obligatorios.")
            return redirect('crear_notificacion_sistema')

        NotificacionSistema.objects.create(
            tipo=tipo, titulo=titulo, mensaje=mensaje, creado_por=request.user, dispara_tour=dispara_tour,  # NUEVO
        )
        messages.success(request, "Notificación publicada correctamente.")
        return redirect('lista_notificaciones_sistema')

    return render(request, 'notificaciones/crear_notificacion.html', {
        'tipo_choices': NotificacionSistema.TIPO_CHOICES,
    })


@login_required
def lista_notificaciones_sistema(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para ver esta pantalla.")
        return redirect('dashboard_inicio')

    notificaciones = NotificacionSistema.objects.all()
    return render(request, 'notificaciones/lista_notificaciones.html', {
        'notificaciones': notificaciones,
    })


@login_required
def editar_notificacion_sistema(request, notif_id):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para ver esta pantalla.")
        return redirect('dashboard_inicio')

    notif = get_object_or_404(NotificacionSistema, id=notif_id)

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        titulo = request.POST.get('titulo', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        dispara_tour = request.POST.get('dispara_tour') == 'on'

        if tipo not in dict(NotificacionSistema.TIPO_CHOICES):
            messages.error(request, "Selecciona un tipo válido.")
            return redirect('editar_notificacion_sistema', notif_id=notif_id)
        if not titulo or not mensaje:
            messages.error(request, "El título y el mensaje son obligatorios.")
            return redirect('editar_notificacion_sistema', notif_id=notif_id)

        notif.tipo = tipo
        notif.titulo = titulo
        notif.mensaje = mensaje
        notif.dispara_tour = dispara_tour
        notif.save()

        messages.success(request, "Notificación actualizada correctamente.")
        return redirect('lista_notificaciones_sistema')

    return render(request, 'notificaciones/editar_notificacion.html', {
        'notif': notif,
        'tipo_choices': NotificacionSistema.TIPO_CHOICES,
    })


@login_required
def desactivar_notificacion_sistema(request, notif_id):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para hacer esto.")
        return redirect('dashboard_inicio')

    notif = get_object_or_404(NotificacionSistema, id=notif_id)
    notif.activa = False
    notif.save(update_fields=['activa'])
    messages.success(request, "Notificación desactivada.")
    return redirect('lista_notificaciones_sistema')


@login_required
@require_POST
def notif_sistema_marcar_leida_ajax(request, notif_id):
    notif = get_object_or_404(NotificacionSistema, id=notif_id)
    NotificacionLeida.objects.get_or_create(notificacion=notif, usuario=request.user)
 
    ids_leidas = set(
        NotificacionLeida.objects.filter(usuario=request.user)
        .values_list('notificacion_id', flat=True)
    )
    count_no_leidas = NotificacionSistema.objects.filter(activa=True).exclude(id__in=ids_leidas).count()
 
    return JsonResponse({'ok': True, 'count': count_no_leidas})
 
 
@login_required
@require_POST
def notif_sistema_marcar_todas_leidas_ajax(request):
    ids_leidas = set(
        NotificacionLeida.objects.filter(usuario=request.user)
        .values_list('notificacion_id', flat=True)
    )
    no_leidas = NotificacionSistema.objects.filter(activa=True).exclude(id__in=ids_leidas)
    NotificacionLeida.objects.bulk_create(
        [NotificacionLeida(notificacion=n, usuario=request.user) for n in no_leidas],
        ignore_conflicts=True,
    )
    return JsonResponse({'ok': True, 'count': 0})
