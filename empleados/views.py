
import csv
import io
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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

from empresas.models import Empresa

from .forms import EmpleadoForm, IncidenciaForm, SolicitudPrestamoForm
from .models import Empleado, Incidencia, SolicitudPrestamo


@login_required
def empleado_crear(request):
    if request.method == 'POST':
        form = EmpleadoForm(request.POST, user=request.user)
        if form.is_valid():
            empleado = form.save(commit=False)
            if not request.user.is_superuser:
                empleado.empresa = request.user.perfilusuario.empresa
            empleado.save()
            return redirect('empleado_lista')
    else:
        form = EmpleadoForm(user=request.user)
    return render(request, 'empleados/crear.html', {'form': form})


@login_required
def empleado_editar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    if not request.user.is_superuser and empleado.empresa != request.user.perfilusuario.empresa:
        return redirect('empleado_lista')
    # Guardamos los valores originales para comparar después de validar el form
    hora_entrada_original = empleado.hora_entrada_esperada
    hora_salida_original = empleado.hora_salida_esperada

    if request.method == 'POST':
        form = EmpleadoForm(request.POST, instance=empleado, user=request.user)
        if form.is_valid():
            nuevo_entrada = form.cleaned_data.get('hora_entrada_esperada')
            nuevo_salida = form.cleaned_data.get('hora_salida_esperada')

            intenta_cambiar_horario = (
                nuevo_entrada != hora_entrada_original or
                nuevo_salida != hora_salida_original
            )

            if intenta_cambiar_horario and empleado.horario_bloqueado and not request.user.is_superuser:
                # Bloqueado: se ignora el cambio de horario, se guarda el resto normal
                form.instance.hora_entrada_esperada = hora_entrada_original
                form.instance.hora_salida_esperada = hora_salida_original
                messages.warning(
                    request,
                    "El horario esperado de este empleado ya fue editado antes y está bloqueado. "
                    "Solo un superusuario puede volver a modificarlo. Se guardaron los demás cambios."
                )
                form.save()
                return redirect('empleado_lista')
            
            form.save()

            # Si de verdad cambió el horario (y se permitió el cambio), bloquear para el futuro
            if intenta_cambiar_horario:
                empleado.refresh_from_db()
                empleado.horario_bloqueado = True
                empleado.save(update_fields=['horario_bloqueado'])
                if not request.user.is_superuser:
                    messages.info(
                        request,
                        "El horario fue actualizado. A partir de ahora, solo un superusuario "
                        "podrá volver a modificarlo."
                    )

            return redirect('empleado_lista')
    else:
        form = EmpleadoForm(instance=empleado, user=request.user)
    return render(request, 'empleados/editar.html', {'form': form, 
                            'empleado': empleado,
                            'horario_bloqueado_para_usuario': empleado.horario_bloqueado and not request.user.is_superuser,})


@login_required
def empleado_lista(request):
    query = request.GET.get('q', '').strip()
    empresa_id = request.session.get("empresa_id")

    if request.user.is_superuser and empresa_id:
        empresa = Empresa.objects.filter(id=empresa_id).first()
        empleados = Empleado.objects.filter(empresa_id=empresa_id, activo=True).order_by('nombre')
    elif request.user.is_superuser:
        empresa = None
        empleados = Empleado.objects.filter(activo=True).order_by('nombre')
    else:
        empresa = request.user.perfilusuario.empresa
        empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('nombre')

    if query:
        empleados = empleados.filter(
            Q(nombre__icontains=query) | Q(rfc__icontains=query)
        )

    paginator = Paginator(empleados, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'empleados/lista.html', {
        'empleados': page_obj,
        'empresa': empresa,
        'q': query,
    })



@login_required
def incidencia_crear(request):
 
    if request.user.is_superuser:
        empleados_qs = Empleado.objects.all()
    else:
        empleados_qs = Empleado.objects.filter(empresa=request.user.perfilusuario.empresa)
    if request.method == 'POST':
        form = IncidenciaForm(request.POST)
        form.fields['empleado'].queryset = empleados_qs
        if form.is_valid():
            incidencia = form.save()
            # NUEVO -- ya NO redirige directo al PDF (eso congelaba la
            # pantalla, porque el navegador dispara una descarga y no hay
            # HTML que renderizar). Ahora redirige a la lista normal, y le
            # pasa un query param para que el PDF se abra solo en una
            # pestana nueva via JavaScript -- la lista si se refresca.
            if incidencia.tipo in ('vacaciones', 'permiso'):
                url = reverse('incidencias_lista') + f'?imprimir={incidencia.tipo}&incidencia_id={incidencia.id}'
                return redirect(url)
            return redirect('incidencias_lista')
    else:
        form = IncidenciaForm()
        form.fields['empleado'].queryset = empleados_qs
    return render(request, 'incidencias/form.html', {'form': form})


@login_required
def incidencias_lista(request):
    fecha_inicio = _fecha_valida(request.GET.get('fecha_inicio'))
    fecha_fin = _fecha_valida(request.GET.get('fecha_fin'))
    empleado_id = request.GET.get('empleado')
    if empleado_id and not empleado_id.isdigit():
        empleado_id = None
 
    if request.user.is_superuser:
        empleados = Empleado.objects.all()
        incidencias = Incidencia.objects.select_related('empleado').order_by('-fecha')
    else:
        empleados = Empleado.objects.filter(empresa=request.user.perfilusuario.empresa)
        incidencias = Incidencia.objects.select_related('empleado').order_by('-fecha')
        incidencias = incidencias.filter(empleado__empresa=request.user.perfilusuario.empresa)
 
    if empleado_id:
        incidencias = incidencias.filter(empleado_id=empleado_id)
    if fecha_inicio:
        incidencias = incidencias.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        incidencias = incidencias.filter(fecha__lte=fecha_fin)
 
    paginator = Paginator(incidencias, 20)
    page_number = request.GET.get('page')
    incidencias_pagina = paginator.get_page(page_number)
 
    return render(request, 'incidencias/lista.html', {
        'incidencias': incidencias_pagina,
        'empleados': empleados,
        'empleado_id': empleado_id,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })



def _fecha_valida(valor):
    """Regresa el valor tal cual si es una fecha ISO valida
    (YYYY-MM-DD); regresa None en cualquier otro caso -- incluyendo
    el texto literal "None" que puede llegar por un link mal armado
    en algun template."""
    if not valor or valor == "None":
        return None
    try:
        date.fromisoformat(valor)
        return valor
    except (ValueError, TypeError):
        return None


@login_required
def exportar_incidencias_excel(request):
    empleado_id = request.GET.get('empleado')
    fecha_inicio = _fecha_valida(request.GET.get('fecha_inicio'))
    fecha_fin = _fecha_valida(request.GET.get('fecha_fin'))
 
    if empleado_id and not empleado_id.isdigit():
        empleado_id = None
 
    if request.user.is_superuser:
        incidencias = Incidencia.objects.select_related('empleado').order_by('-fecha')
        if empleado_id:
            incidencias = incidencias.filter(empleado_id=empleado_id)
    else:
        incidencias = Incidencia.objects.select_related('empleado').order_by('-fecha')
        incidencias = incidencias.filter(empleado__empresa=request.user.perfilusuario.empresa)
        if empleado_id:
            incidencias = incidencias.filter(empleado_id=empleado_id)
 
    if fecha_inicio:
        incidencias = incidencias.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        incidencias = incidencias.filter(fecha__lte=fecha_fin)
 
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="incidencias.csv"'
    writer = csv.writer(response)
    writer.writerow(['Empleado', 'Tipo', 'Fecha inicio', 'Fecha fin', 'Días', 'Descripción'])
    for i in incidencias:
        writer.writerow([
            i.empleado.nombre,
            i.get_tipo_display(),
            i.fecha,
            i.fecha_fin or '',
            i.dias,
            i.descripcion,
        ])
    return response




@login_required
def incidencia_editar(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)

    if not request.user.is_superuser and incidencia.empleado.empresa != request.user.perfilusuario.empresa:
        return redirect('incidencias_lista')

    if request.user.is_superuser:
        empleados_qs = Empleado.objects.all()
    else:
        empleados_qs = Empleado.objects.filter(empresa=request.user.perfilusuario.empresa)

    if request.method == 'POST':
        form = IncidenciaForm(request.POST, instance=incidencia)
        form.fields['empleado'].queryset = empleados_qs
        if form.is_valid():
            form.save()
            return redirect('incidencias_lista')
        
    else:
        form = IncidenciaForm(instance=incidencia)
        form.fields['empleado'].queryset = empleados_qs
    return render(request, 'incidencias/form.html', {'form': form, 'incidencia': incidencia})


@login_required
def incidencia_cancelar(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)
    if not request.user.is_superuser and incidencia.empleado.empresa != request.user.perfilusuario.empresa:
        messages.error(request, "No tienes permiso para eliminar esta incidencia.")
        return redirect('incidencias_lista')
    incidencia.delete()
    messages.success(request, "Incidencia eliminada correctamente.")
    return redirect('incidencias_lista')





##############modulo solicitude prestamo, vacaciones y permisos########################

MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

AZUL = colors.HexColor("#1F4E79")
GRIS = colors.HexColor("#595959")
GRIS_CLARO = colors.HexColor("#F0F4F8")


def _fecha_larga(d):
    if not d:
        return ""
    return f"{d.day} de {MESES_ES[d.month]} de {d.year}"


def _membrete(story, styles, empresa, titulo):
    """Encabezado compartido por las 3 solicitudes -- nombre de la
    empresa, titulo del documento, y una linea divisoria."""
    estilo_empresa = ParagraphStyle(
        "Empresa", parent=styles["Normal"], fontSize=14, textColor=AZUL,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=2,
    )
    estilo_titulo = ParagraphStyle(
        "TituloDoc", parent=styles["Normal"], fontSize=16, textColor=colors.HexColor("#1A1A1A"),
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceBefore=10, spaceAfter=14,
    )
    story.append(Paragraph(empresa.nombre if empresa else "GESAC", estilo_empresa))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL, spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(titulo, estilo_titulo))


def _datos_empleado_tabla(empleado):
    """Tabla de 2 columnas con los datos base del empleado, reutilizada
    en las 3 solicitudes."""
    filas = [
        ["Nombre:", empleado.nombre],
        ["Puesto:", empleado.get_puesto_display() if hasattr(empleado, "get_puesto_display") else ""],
        ["Departamento:", empleado.get_departamento_display() if hasattr(empleado, "get_departamento_display") else ""],
        ["Fecha de solicitud:", _fecha_larga(date.today())],  # noqa: DTZ011
    ]
    t = Table(filas, colWidths=[4.5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), GRIS),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _bloque_firmas(*etiquetas):
    """Genera N lineas de firma lado a lado (ej. 'Empleado', 'Jefe directo')."""
    styles = getSampleStyleSheet()
    estilo_firma = ParagraphStyle(
        "Firma", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, textColor=GRIS,
    )
    fila_lineas = ["_________________________" for _ in etiquetas]
    fila_etiquetas = [Paragraph(e, estilo_firma) for e in etiquetas]
    ancho_col = 17 * cm / len(etiquetas)
    t = Table([fila_lineas, fila_etiquetas], colWidths=[ancho_col] * len(etiquetas))
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 40),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
    ]))
    return t


# ============================================================
# 1. SOLICITUD DE VACACIONES
# ============================================================
@login_required
def generar_solicitud_vacaciones_pdf(request, incidencia_id):
    incidencia = get_object_or_404(Incidencia, id=incidencia_id, tipo="vacaciones")
    empleado = incidencia.empleado
    empresa = getattr(empleado, "empresa", None)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    _membrete(story, styles, empresa, "Solicitud de Vacaciones")
    story.append(_datos_empleado_tabla(empleado))
    story.append(Spacer(1, 14))

    filas_periodo = [
        ["Del:", _fecha_larga(incidencia.fecha)],
        ["Al:", _fecha_larga(incidencia.fecha_fin or incidencia.fecha)],
        ["Total de dias:", str(incidencia.dias)],
    ]
    t_periodo = Table(filas_periodo, colWidths=[4.5 * cm, 11 * cm])
    t_periodo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_periodo)
    story.append(Spacer(1, 16))

    if incidencia.descripcion:
        story.append(Paragraph("<b>Observaciones:</b>", styles["Normal"]))
        story.append(Paragraph(incidencia.descripcion, styles["Normal"]))
        story.append(Spacer(1, 16))

    story.append(Spacer(1, 30))
    story.append(_bloque_firmas("Firma del empleado", "Firma del jefe directo / RH"))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="solicitud_vacaciones_{empleado.nombre.replace(" ", "_")}.pdf"'
    return response


# ============================================================
# 2. SOLICITUD DE PERMISO
# ============================================================
@login_required
def generar_solicitud_permiso_pdf(request, incidencia_id):
    incidencia = get_object_or_404(Incidencia, id=incidencia_id, tipo="permiso")
    empleado = incidencia.empleado
    empresa = getattr(empleado, "empresa", None)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    _membrete(story, styles, empresa, "Solicitud de Permiso")
    story.append(_datos_empleado_tabla(empleado))
    story.append(Spacer(1, 14))

    filas_periodo = [
        ["Del:", _fecha_larga(incidencia.fecha)],
        ["Al:", _fecha_larga(incidencia.fecha_fin or incidencia.fecha)],
        ["Total de dias:", str(incidencia.dias)],
    ]
    t_periodo = Table(filas_periodo, colWidths=[4.5 * cm, 11 * cm])
    t_periodo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_periodo)
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>Motivo del permiso:</b>", styles["Normal"]))
    story.append(Paragraph(incidencia.descripcion or "—", styles["Normal"]))
    story.append(Spacer(1, 30))

    story.append(_bloque_firmas("Firma del empleado", "Firma del jefe directo / RH"))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="solicitud_permiso_{empleado.nombre.replace(" ", "_")}.pdf"'
    return response


# ============================================================
# 3. SOLICITUD DE PRESTAMO
# ============================================================
@login_required
def generar_solicitud_prestamo_pdf(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudPrestamo, id=solicitud_id)
    empleado = solicitud.empleado
    empresa = getattr(empleado, "empresa", None)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    _membrete(story, styles, empresa, "Solicitud de Préstamo")
    story.append(_datos_empleado_tabla(empleado))
    story.append(Spacer(1, 14))

    filas_prestamo = [
        ["Monto solicitado:", f"${solicitud.monto:,.2f}"],
        ["Número de parcialidades:", str(solicitud.numero_parcialidades)],
        ["Monto por parcialidad:", f"${solicitud.monto_parcialidad:,.2f}" if solicitud.monto_parcialidad else "—"],
        ["Fecha primer descuento:", _fecha_larga(solicitud.fecha_primer_descuento) if solicitud.fecha_primer_descuento else "—"],
    ]
    t_prestamo = Table(filas_prestamo, colWidths=[5.5 * cm, 10 * cm])
    t_prestamo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_prestamo)
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>Motivo:</b>", styles["Normal"]))
    story.append(Paragraph(solicitud.motivo or "—", styles["Normal"]))
    story.append(Spacer(1, 16))

    texto_autorizacion = (
        "Autorizo a la empresa a descontar de mi nómina el monto de la parcialidad indicada arriba, "
        "en cada uno de los periodos de pago correspondientes, hasta liquidar por completo el préstamo solicitado."
    )
    story.append(Paragraph(texto_autorizacion, ParagraphStyle(
        "Autorizacion", parent=styles["Normal"], fontSize=9, textColor=GRIS, spaceBefore=6,
    )))

    story.append(Spacer(1, 30))
    story.append(_bloque_firmas("Firma del empleado", "Firma del jefe directo / RH"))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="solicitud_prestamo_{empleado.nombre.replace(" ", "_")}.pdf"'
    return response



@login_required
def solicitud_prestamo_crear(request):
    if request.user.is_superuser:
        empleados_qs = Empleado.objects.all()
    else:
        empleados_qs = Empleado.objects.filter(empresa=request.user.perfilusuario.empresa)
 
    if request.method == 'POST':
        form = SolicitudPrestamoForm(request.POST)
        form.fields['empleado'].queryset = empleados_qs
        if form.is_valid():
            solicitud = form.save()
            # NUEVO -- ya NO redirige directo al PDF (congelaba la
            # pantalla). Redirige a la lista de Incidencias, con un
            # parametro para que el PDF se abra solo en una pestana
            # nueva via JavaScript -- la pantalla si se refresca.
            url = reverse('incidencias_lista') + f'?imprimir=prestamo&incidencia_id={solicitud.id}'
            return redirect(url)
    else:
        form = SolicitudPrestamoForm()
        form.fields['empleado'].queryset = empleados_qs
    return render(request, 'empleados/form_prestamo.html', {'form': form})


def _fecha_valida(valor):
    from datetime import date
    if not valor or valor == "None":
        return None
    try:
        date.fromisoformat(valor)
        return valor
    except (ValueError, TypeError):
        return None
 
 
@login_required
def solicitudes_prestamo_lista(request):
    empleado_id = request.GET.get('empleado')
    if empleado_id and not empleado_id.isdigit():
        empleado_id = None
    estatus = request.GET.get('estatus')
    fecha_inicio = _fecha_valida(request.GET.get('fecha_inicio'))
    fecha_fin = _fecha_valida(request.GET.get('fecha_fin'))
 
    if request.user.is_superuser:
        empleados = Empleado.objects.all()
        solicitudes = SolicitudPrestamo.objects.select_related('empleado').order_by('-fecha_solicitud')
    else:
        empleados = Empleado.objects.filter(empresa=request.user.perfilusuario.empresa)
        solicitudes = SolicitudPrestamo.objects.select_related('empleado').order_by('-fecha_solicitud')
        solicitudes = solicitudes.filter(empleado__empresa=request.user.perfilusuario.empresa)
 
    if empleado_id:
        solicitudes = solicitudes.filter(empleado_id=empleado_id)
    if estatus:
        solicitudes = solicitudes.filter(estatus=estatus)
    if fecha_inicio:
        solicitudes = solicitudes.filter(fecha_solicitud__gte=fecha_inicio)
    if fecha_fin:
        solicitudes = solicitudes.filter(fecha_solicitud__lte=fecha_fin)
 
    paginator = Paginator(solicitudes, 20)
    page_number = request.GET.get('page')
    solicitudes_pagina = paginator.get_page(page_number)
 
    return render(request, 'empleados/solicitudes_prestamo_lista.html', {
        'solicitudes': solicitudes_pagina,
        'empleados': empleados,
        'empleado_id': empleado_id,
        'estatus_filtro': estatus,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estatus_choices': SolicitudPrestamo.ESTATUS_CHOICES,
    })
 
 
@login_required
def solicitud_prestamo_cambiar_estatus(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudPrestamo, id=solicitud_id)
 
    if request.method == 'POST':
        nuevo_estatus = request.POST.get('estatus')
        valores_validos = [c[0] for c in SolicitudPrestamo.ESTATUS_CHOICES]
        if nuevo_estatus in valores_validos:
            solicitud.estatus = nuevo_estatus
            solicitud.save(update_fields=['estatus'])
            messages.success(request, f"Estatus actualizado a \"{solicitud.get_estatus_display()}\".")
        else:
            messages.error(request, "Estatus no válido.")
 
    next_url = request.GET.get('next')
    return redirect(next_url or 'solicitudes_prestamo_lista')

