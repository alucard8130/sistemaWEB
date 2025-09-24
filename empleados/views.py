
import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from gastos.models import Gasto
from .forms import EmpleadoForm, IncidenciaForm
from .models import Empleado, Incidencia


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

    if request.method == 'POST':
        form = EmpleadoForm(request.POST, instance=empleado, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('empleado_lista')
    else:
        form = EmpleadoForm(instance=empleado, user=request.user)
    return render(request, 'empleados/editar.html', {'form': form, 'empleado': empleado})

@login_required
def empleado_lista(request):
    empresa_id = request.session.get("empresa_id")
    if request.user.is_superuser and empresa_id:
        empleados = Empleado.objects.filter(empresa_id=empresa_id, activo=True).order_by('nombre')
    elif request.user.is_superuser:
        empleados = Empleado.objects.filter(activo=True).order_by('nombre')
    else:
        empresa = request.user.perfilusuario.empresa
        empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    return render(request, 'empleados/lista.html', {'empleados': empleados})


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
            form.save()
            return redirect('incidencias_lista')
    else:
        form = IncidenciaForm()
        form.fields['empleado'].queryset = empleados_qs
    return render(request, 'incidencias/form.html', {'form': form})



@login_required
def incidencias_lista(request):

    if request.user.is_superuser:
        empleados = Empleado.objects.all()
    else:
        empleados = Empleado.objects.filter(empresa=request.user.perfilusuario.empresa)
        empleado_id = request.GET.get('empleado')
        incidencias = Incidencia.objects.select_related('empleado').order_by('-fecha')
        if not request.user.is_superuser:
            incidencias = incidencias.filter(empleado__empresa=request.user.perfilusuario.empresa)
        if empleado_id:
            incidencias = incidencias.filter(empleado_id=empleado_id)
    return render(request, 'incidencias/lista.html', {
        'incidencias': incidencias,
        'empleados': empleados,
        'empleado_id': empleado_id,
    })

@login_required
def exportar_incidencias_excel(request):
    empleado_id = request.GET.get('empleado')
    incidencias = Incidencia.objects.select_related('empleado').order_by('-fecha')
    if not request.user.is_superuser:
        incidencias = incidencias.filter(empleado__empresa=request.user.perfilusuario.empresa)
    if empleado_id:
        incidencias = incidencias.filter(empleado_id=empleado_id)

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

