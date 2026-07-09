"""Vistas del control de asistencia. Acceso público vía link único por
empleado (token UUID) -- no requieren login, el token ya identifica al
empleado. El link debe compartirse solo con el empleado correspondiente
(por WhatsApp, código QR impreso, etc.) ya que actúa como credencial."""

import json
from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Empleado, RegistroAsistencia, Incidencia
from .utils import calcular_distancia_metros


def marcar_asistencia(request, token):
    """Página que ve el empleado en su celular al abrir su link único."""
    empleado = get_object_or_404(Empleado, token_asistencia=token, activo=True)
    hoy = timezone.localdate()
    registro = RegistroAsistencia.objects.filter(empleado=empleado, fecha=hoy).first()

    contexto = {
        'empleado': empleado,
        'registro': registro,
        'puede_marcar_entrada': registro is None or registro.hora_entrada is None,
        'puede_marcar_salida': bool(registro and registro.hora_entrada and not registro.hora_salida),
        'ya_completo': bool(registro and registro.hora_entrada and registro.hora_salida),
        'token': token,
    }
    return render(request, 'empleados/marcar_asistencia.html', contexto)


def _registrar_retardo_si_aplica(empleado, ahora, hoy):
    """Crea una Incidencia tipo 'retardo' automáticamente si la hora de
    entrada real pasa la hora esperada + tolerancia. No duplica si ya
    existe una incidencia de retardo para ese empleado ese día."""
    if not empleado.hora_entrada_esperada:
        return

    limite_naive = datetime.combine(hoy, empleado.hora_entrada_esperada) + timedelta(minutes=empleado.tolerancia_minutos)
    limite = timezone.make_aware(limite_naive) if timezone.is_naive(limite_naive) else limite_naive

    if ahora > limite:
        Incidencia.objects.get_or_create(
            empleado=empleado,
            tipo='retardo',
            fecha=hoy,
            defaults={
                'descripcion': f"Retardo detectado automáticamente por el checador: entró a las {timezone.localtime(ahora).strftime('%H:%M')} "
                               f"(esperado: {empleado.hora_entrada_esperada.strftime('%H:%M')})"
            }
        )


@require_POST
def api_marcar_entrada(request, token):
    empleado = get_object_or_404(Empleado, token_asistencia=token, activo=True)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    lat = data.get('lat')
    lng = data.get('lng')

    hoy = timezone.localdate()
    ahora = timezone.localtime()

    registro, _creado = RegistroAsistencia.objects.get_or_create(empleado=empleado, fecha=hoy)

    if registro.hora_entrada:
        return JsonResponse({'error': 'Ya marcaste tu entrada hoy.'}, status=400)

    registro.hora_entrada = ahora
    registro.lat_entrada = lat
    registro.lng_entrada = lng

    empresa = empleado.empresa
    if lat is not None and lng is not None and empresa and empresa.lat_oficina and empresa.lng_oficina:
        distancia = calcular_distancia_metros(lat, lng, empresa.lat_oficina, empresa.lng_oficina)
        registro.distancia_metros_entrada = distancia
        registro.dentro_de_rango_entrada = distancia <= empresa.radio_permitido_metros
    else:
        # Sin ubicación de oficina configurada, o el navegador no dio
        # coordenadas: se registra igual, sin poder validar el rango.
        registro.dentro_de_rango_entrada = None

    registro.save()

    _registrar_retardo_si_aplica(empleado, ahora, hoy)

    mensaje = "✅ Entrada registrada correctamente."
    if registro.dentro_de_rango_entrada is False:
        mensaje += " ⚠️ Pareces estar fuera del rango permitido; quedó marcado para revisión."

    return JsonResponse({'ok': True, 'mensaje': mensaje, 'hora': ahora.strftime('%H:%M')})


@require_POST
def api_marcar_salida(request, token):
    empleado = get_object_or_404(Empleado, token_asistencia=token, activo=True)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    lat = data.get('lat')
    lng = data.get('lng')

    hoy = timezone.localdate()
    ahora = timezone.localtime()

    registro = RegistroAsistencia.objects.filter(empleado=empleado, fecha=hoy).first()
    if not registro or not registro.hora_entrada:
        return JsonResponse({'error': 'Primero debes marcar tu entrada.'}, status=400)
    if registro.hora_salida:
        return JsonResponse({'error': 'Ya marcaste tu salida hoy.'}, status=400)

    registro.hora_salida = ahora
    registro.lat_salida = lat
    registro.lng_salida = lng

    empresa = empleado.empresa
    if lat is not None and lng is not None and empresa and empresa.lat_oficina and empresa.lng_oficina:
        distancia = calcular_distancia_metros(lat, lng, empresa.lat_oficina, empresa.lng_oficina)
        registro.distancia_metros_salida = distancia
        registro.dentro_de_rango_salida = distancia <= empresa.radio_permitido_metros
    else:
        registro.dentro_de_rango_salida = None

    registro.save()

    mensaje = "✅ Salida registrada correctamente."
    if registro.dentro_de_rango_salida is False:
        mensaje += " ⚠️ Pareces estar fuera del rango permitido; quedó marcado para revisión."

    return JsonResponse({'ok': True, 'mensaje': mensaje, 'hora': ahora.strftime('%H:%M')})