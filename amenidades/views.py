from datetime import datetime, timedelta
from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from core import settings
from facturacion.models import FacturaOtrosIngresos, TipoOtroIngreso
from .models import Amenidad, Reservacion
from principal.models import VisitanteAcceso  # ajusta si vive en otra app
from locales.models import LocalComercial
from areas.models import AreaComun
import re as re_module
from django.contrib.auth.decorators import login_required




def _visitante_actual(request):
    visitante_id = request.session.get('visitante_id')
    if not visitante_id:
        return None
    return VisitanteAcceso.objects.filter(id=visitante_id, activo=True).first()


def _propiedades_del_visitante(request):
    """Mismo patrón que visitante_consulta_facturas: sesión + empresa_id."""
    visitante = _visitante_actual(request)
    if not visitante:
        return None, None, None, None

    empresa_id = request.session.get('empresa_id')

    locales = LocalComercial.objects.filter(id__in=visitante.locales.all(), activo=True)
    areas = AreaComun.objects.filter(id__in=visitante.areas.all(), activo=True)
    if empresa_id:
        locales = locales.filter(empresa_id=empresa_id)
        areas = areas.filter(empresa_id=empresa_id)

    empresa = None
    if locales.exists():
        empresa = locales.first().empresa
    elif areas.exists():
        empresa = areas.first().empresa

    return visitante, locales, areas, empresa


def lista_amenidades(request):
    visitante, locales, areas, empresa = _propiedades_del_visitante(request)
    if not visitante:
        return redirect('visitante_login')
    if not empresa:
        messages.error(request, "No se encontró tu propiedad asociada.")
        return redirect('visitante_seleccionar_empresa')

    amenidades = Amenidad.objects.filter(empresa=empresa, activa=True).order_by('nombre')

    return render(request, 'amenidades/lista.html', {
        'amenidades': amenidades,
        'empresa': empresa,
    })


def reservar_amenidad(request, amenidad_id):
    visitante, locales, areas, empresa = _propiedades_del_visitante(request)
    if not visitante:
        return redirect('visitante_login')
    if not empresa:
        messages.error(request, "No se encontró tu propiedad asociada.")
        return redirect('visitante_seleccionar_empresa')

    amenidad = get_object_or_404(Amenidad, pk=amenidad_id, empresa=empresa, activa=True)

    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        hora_inicio_str = request.POST.get('hora_inicio')
        hora_fin_str = request.POST.get('hora_fin')
        numero_invitados = request.POST.get('numero_invitados') or None
        observaciones = request.POST.get('observaciones', '').strip()

        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
            hora_fin = datetime.strptime(hora_fin_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(request, "Fecha u hora inválida.")
            return redirect('reservar_amenidad', amenidad_id=amenidad_id)

        if hora_fin <= hora_inicio:
            messages.error(request, "La hora de fin debe ser posterior a la hora de inicio.")
            return redirect('reservar_amenidad', amenidad_id=amenidad_id)

        if hora_inicio < amenidad.hora_apertura or hora_fin > amenidad.hora_cierre:
            messages.error(
                request,
                f"La amenidad solo está disponible de {amenidad.hora_apertura} a {amenidad.hora_cierre}."
            )
            return redirect('reservar_amenidad', amenidad_id=amenidad_id)

        duracion_horas = (
            datetime.combine(fecha, hora_fin) - datetime.combine(fecha, hora_inicio)
        ).total_seconds() / 3600
        if duracion_horas > amenidad.duracion_maxima_horas:
            messages.error(
                request,
                f"La duración máxima permitida es de {amenidad.duracion_maxima_horas} horas."
            )
            return redirect('reservar_amenidad', amenidad_id=amenidad_id)

        fecha_minima = datetime.now().date() + timedelta(days=amenidad.dias_anticipacion_minima)
        if fecha < fecha_minima:
            messages.error(
                request,
                f"Debes reservar con al menos {amenidad.dias_anticipacion_minima} día(s) de anticipación."
            )
            return redirect('reservar_amenidad', amenidad_id=amenidad_id)

        traslape = Reservacion.objects.filter(
            amenidad=amenidad, fecha=fecha, estado='confirmada',
            hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio,
        ).exists()
        if traslape:
            messages.error(request, "Ese horario ya está ocupado. Elige otro horario.")
            return redirect('reservar_amenidad', amenidad_id=amenidad_id)

        propiedad = locales.first()
        cliente = propiedad.cliente if propiedad else None

        if not cliente:
            messages.error(request, "Tu propiedad no tiene un cliente asociado. Contacta al administrador.")
            return redirect('lista_amenidades')

        reservacion = Reservacion.objects.create(
            empresa=empresa,
            amenidad=amenidad,
            cliente=cliente,
            propiedad=propiedad,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            numero_invitados=numero_invitados,
            observaciones=observaciones,
        )

        if amenidad.costo_reservacion > 0:
            tipo_ingreso, _ = TipoOtroIngreso.objects.get_or_create(
                empresa=empresa, nombre='Reservación de Amenidades'
            )
            prefix = "AMEN-"
            with transaction.atomic():
                for intento in range(5):
                    try:
                        last_folio = (
                            FacturaOtrosIngresos.objects.select_for_update()
                            .filter(empresa=empresa, folio__startswith=prefix)
                            .order_by('-folio').values_list('folio', flat=True).first()
                        )
                        last_num = int(last_folio.replace(prefix, "")) if last_folio and re_module.match(r'^AMEN-\d{5}$', last_folio) else 0
                        folio = f"{prefix}{last_num + 1:05d}"
                        factura_oi = FacturaOtrosIngresos.objects.create(
                            empresa=empresa,
                            cliente=cliente,
                            tipo_ingreso=tipo_ingreso,
                            folio=folio,
                            fecha_vencimiento=fecha,
                            monto=amenidad.costo_reservacion,
                            observaciones=f"Reservación de {amenidad.nombre} el {fecha}",
                            estatus='pendiente',
                        )
                        reservacion.factura_generada = factura_oi
                        reservacion.save(update_fields=['factura_generada'])
                        break
                    except IntegrityError:
                        continue

        if visitante.email:
            mensaje = (
                f"Hola {visitante.nombre or visitante.username},\n\n"
                f"Tu reservación ha sido confirmada:\n\n"
                f"Amenidad: {amenidad.nombre}\n"
                f"Fecha: {fecha.strftime('%d/%m/%Y')}\n"
                f"Horario: {hora_inicio.strftime('%H:%M')} a {hora_fin.strftime('%H:%M')}\n"
            )
            if numero_invitados:
                mensaje += f"Invitados: {numero_invitados}\n"
            if amenidad.costo_reservacion > 0:
                mensaje += f"\nCosto de la reservación: ${amenidad.costo_reservacion:,.2f} (consulta tu estado de cuenta para el pago).\n"
            mensaje += (
                f"\nSi necesitas cancelar, puedes hacerlo desde el portal en 'Mis Reservaciones'.\n\n"
                f"Atentamente,\n{empresa.nombre}"
            )

            send_mail(
                f"Confirmación de reservación — {amenidad.nombre}",
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [visitante.email],
                fail_silently=True,
            )                
                        
        messages.success(request, f"✅ Reservación confirmada: {amenidad.nombre} el {fecha} de {hora_inicio} a {hora_fin}.")
        return redirect('mis_reservaciones')

    reservaciones_futuras = Reservacion.objects.filter(
        amenidad=amenidad, fecha__gte=datetime.now().date(), estado='confirmada'
    ).order_by('fecha', 'hora_inicio')

    return render(request, 'amenidades/reservar.html', {
        'amenidad': amenidad,
        'reservaciones_futuras': reservaciones_futuras,
    })


def mis_reservaciones(request):
    visitante, locales, areas, empresa = _propiedades_del_visitante(request)
    if not visitante:
        return redirect('visitante_login')
    if not empresa:
        messages.error(request, "No se encontró tu propiedad asociada.")
        return redirect('visitante_seleccionar_empresa')

    propiedad = locales.first()
    cliente = propiedad.cliente if propiedad else None

    reservaciones = Reservacion.objects.filter(
        empresa=empresa, cliente=cliente
    ).select_related('amenidad').order_by('-fecha', '-hora_inicio')

    return render(request, 'amenidades/mis_reservaciones.html', {
        'reservaciones': reservaciones,
    })


def cancelar_reservacion(request, reservacion_id):
    visitante, locales, areas, empresa = _propiedades_del_visitante(request)
    if not visitante:
        return redirect('visitante_login')

    propiedad = locales.first() if locales else None
    cliente = propiedad.cliente if propiedad else None

    reservacion = get_object_or_404(
        Reservacion, pk=reservacion_id, empresa=empresa, cliente=cliente, estado='confirmada'
    )

    if request.method == 'POST':
        reservacion.estado = 'cancelada'
        reservacion.save()
        messages.success(request, "Reservación cancelada.")
        return redirect('mis_reservaciones')

    return render(request, 'amenidades/confirmar_cancelar.html', {'reservacion': reservacion})




##############APP AMENIDADES PARA USUARIOS GESAC####################

def _empresa_del_usuario(request):
    if request.user.is_superuser:
        empresa_id = request.session.get('empresa_id')
        from empresas.models import Empresa
        return Empresa.objects.filter(id=empresa_id).first() if empresa_id else None
    perfil = getattr(request.user, 'perfilusuario', None)
    return perfil.empresa if perfil else None


@login_required
def lista_amenidades_config(request):
    empresa = _empresa_del_usuario(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect('dashboard_inicio')

    amenidades = Amenidad.objects.filter(empresa=empresa).order_by('nombre')

    return render(request, 'amenidades/config_lista.html', {
        'amenidades': amenidades,
    })


@login_required
def crear_amenidad(request):
    empresa = _empresa_del_usuario(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect('dashboard_inicio')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        capacidad_maxima = request.POST.get('capacidad_maxima') or None
        hora_apertura = request.POST.get('hora_apertura') or '08:00'
        hora_cierre = request.POST.get('hora_cierre') or '22:00'
        duracion_maxima_horas = request.POST.get('duracion_maxima_horas') or 4
        costo_reservacion = request.POST.get('costo_reservacion') or 0
        requiere_deposito = request.POST.get('requiere_deposito') == 'on'
        monto_deposito = request.POST.get('monto_deposito') or 0
        dias_anticipacion_minima = request.POST.get('dias_anticipacion_minima') or 1

        if not nombre:
            messages.error(request, "El nombre de la amenidad es obligatorio.")
            return redirect('crear_amenidad')

        if Amenidad.objects.filter(empresa=empresa, nombre__iexact=nombre).exists():
            messages.error(request, f"Ya existe una amenidad llamada '{nombre}'.")
            return redirect('crear_amenidad')

        try:
            Amenidad.objects.create(
                empresa=empresa,
                nombre=nombre,
                descripcion=descripcion,
                capacidad_maxima=capacidad_maxima,
                hora_apertura=hora_apertura,
                hora_cierre=hora_cierre,
                duracion_maxima_horas=duracion_maxima_horas,
                costo_reservacion=costo_reservacion,
                requiere_deposito=requiere_deposito,
                monto_deposito=monto_deposito,
                dias_anticipacion_minima=dias_anticipacion_minima,
                activa=True,
            )
        except Exception as e:
            messages.error(request, f"No se pudo crear la amenidad: {e}")
            return redirect('crear_amenidad')

        messages.success(request, f"Amenidad '{nombre}' creada correctamente.")
        return redirect('lista_amenidades_config')

    return render(request, 'amenidades/config_form.html', {'amenidad': None})


@login_required
def editar_amenidad(request, amenidad_id):
    empresa = _empresa_del_usuario(request)
    amenidad = get_object_or_404(Amenidad, pk=amenidad_id, empresa=empresa)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, "El nombre de la amenidad es obligatorio.")
            return redirect('editar_amenidad', amenidad_id=amenidad_id)

        duplicado = Amenidad.objects.filter(empresa=empresa, nombre__iexact=nombre).exclude(pk=amenidad.pk)
        if duplicado.exists():
            messages.error(request, f"Ya existe otra amenidad llamada '{nombre}'.")
            return redirect('editar_amenidad', amenidad_id=amenidad_id)

        amenidad.nombre = nombre
        amenidad.descripcion = request.POST.get('descripcion', '').strip()
        amenidad.capacidad_maxima = request.POST.get('capacidad_maxima') or None
        amenidad.hora_apertura = request.POST.get('hora_apertura') or amenidad.hora_apertura
        amenidad.hora_cierre = request.POST.get('hora_cierre') or amenidad.hora_cierre
        amenidad.duracion_maxima_horas = request.POST.get('duracion_maxima_horas') or amenidad.duracion_maxima_horas
        amenidad.costo_reservacion = request.POST.get('costo_reservacion') or 0
        amenidad.requiere_deposito = request.POST.get('requiere_deposito') == 'on'
        amenidad.monto_deposito = request.POST.get('monto_deposito') or 0
        amenidad.dias_anticipacion_minima = request.POST.get('dias_anticipacion_minima') or 1
        amenidad.activa = request.POST.get('activa') == 'on'
        amenidad.save()

        messages.success(request, f"Amenidad '{amenidad.nombre}' actualizada.")
        return redirect('lista_amenidades_config')

    return render(request, 'amenidades/config_form.html', {'amenidad': amenidad})


@login_required
def eliminar_amenidad(request, amenidad_id):
    empresa = _empresa_del_usuario(request)
    amenidad = get_object_or_404(Amenidad, pk=amenidad_id, empresa=empresa)

    if request.method == 'POST':
        # Soft-delete: se desactiva en vez de borrar, para conservar el
        # historial de reservaciones ya hechas contra esta amenidad.
        amenidad.activa = False
        amenidad.save()
        messages.success(request, f"Amenidad '{amenidad.nombre}' desactivada.")
        return redirect('lista_amenidades_config')

    return render(request, 'amenidades/config_confirmar_eliminar.html', {'amenidad': amenidad})


@login_required
def calendario_reservaciones(request):
    empresa = _empresa_del_usuario(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect('dashboard_inicio')

    amenidades = Amenidad.objects.filter(empresa=empresa).order_by('nombre')

    return render(request, 'amenidades/calendario.html', {
        'amenidades': amenidades,
    })


@login_required
def api_eventos_reservaciones(request):
    """Devuelve las reservaciones en el formato que espera FullCalendar."""
    empresa = _empresa_del_usuario(request)
    if not empresa:
        return JsonResponse([], safe=False)

    amenidad_id = request.GET.get('amenidad_id')

    reservaciones = Reservacion.objects.filter(empresa=empresa).select_related(
        'amenidad', 'cliente', 'propiedad'
    )
    if amenidad_id:
        reservaciones = reservaciones.filter(amenidad_id=amenidad_id)

    COLOR_POR_ESTADO = {
        'confirmada': '#198754',
        'cancelada': '#adb5bd',
    }

    eventos = []
    for r in reservaciones:
        propiedad_texto = r.propiedad.numero if r.propiedad else "—"
        titulo = f"{r.amenidad.nombre} — {propiedad_texto}"

        eventos.append({
            'id': r.id,
            'title': titulo,
            'start': f"{r.fecha.isoformat()}T{r.hora_inicio.strftime('%H:%M:%S')}",
            'end': f"{r.fecha.isoformat()}T{r.hora_fin.strftime('%H:%M:%S')}",
            'color': COLOR_POR_ESTADO.get(r.estado, '#6c757d'),
            'extendedProps': {
                'amenidad': r.amenidad.nombre,
                'propiedad': propiedad_texto,
                'cliente': r.cliente.nombre if r.cliente else "—",
                'estado': r.get_estado_display(),
                'invitados': r.numero_invitados or "—",
                'observaciones': r.observaciones or "—",
            }
        })

    return JsonResponse(eventos, safe=False)    