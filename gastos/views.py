
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from empleados.models import Empleado
from proveedores.models import Proveedor
from .forms import GastoForm, SubgrupoGastoForm, TipoGastoForm
from .models import Gasto, SubgrupoGasto, TipoGasto

# Create your views here.
@login_required
def subgrupo_gasto_crear(request):
    if request.method == 'POST':
        form = SubgrupoGastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('subgrupos_gasto_lista')
    else:
        form = SubgrupoGastoForm()
    return render(request, 'gastos/subgrupo_crear.html', {'form': form})

@login_required
def subgrupos_gasto_lista(request):
    subgrupos = SubgrupoGasto.objects.select_related('grupo').order_by('grupo__nombre', 'nombre')
    return render(request, 'gastos/subgrupos_lista.html', {'subgrupos': subgrupos})

@login_required
def tipos_gasto_lista(request):
    tipos = TipoGasto.objects.select_related('subgrupo__grupo').all()
    return render(request, 'gastos/tipos_gasto_lista.html', {'tipos': tipos})

@login_required
def tipo_gasto_crear(request):
    if request.method == 'POST':
        form = TipoGastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tipos_gasto_lista')
    else:
        form = TipoGastoForm()
    return render(request, 'gastos/tipo_gasto_form.html', {'form': form, 'modo': 'crear'})

@login_required
def tipo_gasto_editar(request, pk):
    tipo = get_object_or_404(TipoGasto, pk=pk)
    if request.method == 'POST':
        form = TipoGastoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            return redirect('tipos_gasto_lista')
    else:
        form = TipoGastoForm(instance=tipo)
    return render(request, 'gastos/tipo_gasto_form.html', {'form': form, 'modo': 'editar', 'tipo': tipo})

@login_required
def tipo_gasto_eliminar(request, pk):
    tipo = get_object_or_404(TipoGasto, pk=pk)
    if request.method == 'POST':
        tipo.delete()
        return redirect('tipos_gasto_lista')
    return render(request, 'gastos/tipo_gasto_confirmar_eliminar.html', {'tipo': tipo})

@login_required
def gastos_lista(request):
    gastos = Gasto.objects.all()
    proveedores = Proveedor.objects.filter(activo=True)
    empleados = Empleado.objects.filter(activo=True)
    #tipos_gasto = Gasto.objects.values_list('tipo_gasto', flat=True).distinct()
    #tipos_gasto = Gasto._meta.get_field('tipo_gasto').choices
    tipos_gasto = TipoGasto.objects.all()

    proveedor_id = request.GET.get('proveedor')
    empleado_id = request.GET.get('empleado')
    tipo_gasto = request.GET.get('tipo_gasto')

    if request.user.is_superuser:
        gastos = Gasto.objects.all().select_related('empresa', 'proveedor', 'empleado', 'tipo_gasto')
    else:
        gastos = Gasto.objects.filter(empresa=request.user.perfilusuario.empresa)

    if proveedor_id:
        gastos = gastos.filter(proveedor_id=proveedor_id)
    if empleado_id:
        gastos = gastos.filter(empleado_id=empleado_id)
    if tipo_gasto:
        gastos = gastos.filter(tipo_gasto=tipo_gasto)

    return render(request, 'gastos/lista.html', {
        'gastos': gastos,                                         
        'proveedores': proveedores,
        'empleados': empleados,
        'tipos_gasto': tipos_gasto,
        'proveedor_id': proveedor_id,
        'empleado_id': empleado_id,
        'tipo_gasto_sel': tipo_gasto,
        })

@login_required
def gasto_nuevo(request):
    if request.method == 'POST':
        form = GastoForm(request.POST or None, request.FILES, user=request.user)
        if form.is_valid():
            gasto = form.save(commit=False)
            origen = form.cleaned_data['origen_tipo']
            if origen == 'proveedor':
                gasto.empleado = None
            elif origen == 'empleado':
                gasto.proveedor = None

            if not request.user.is_superuser:
                gasto.empresa = request.user.perfilusuario.empresa

            gasto.save()
            return redirect('gastos_lista')
    else:
        form = GastoForm(user=request.user)
        if not request.user.is_superuser:
            form.fields['empresa'].initial = request.user.perfilusuario.empresa
    return render(request, 'gastos/form.html', {'form': form, 'modo': 'crear'})

@login_required
def gasto_editar(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    if not request.user.is_superuser and gasto.empresa != request.user.perfilusuario.empresa:
        return redirect('gastos_lista')
    if request.method == 'POST':
        form = GastoForm(request.POST or None, request.FILES, instance=gasto, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('gastos_lista')
    else:
        form = GastoForm(instance=gasto, user=request.user)
    return render(request, 'gastos/form.html', {'form': form, 'modo': 'editar', 'gasto': gasto})

@login_required
def gasto_eliminar(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    if request.method == 'POST':
        gasto.delete()
        return redirect('gastos_lista')
    return render(request, 'gastos/confirmar_eliminar.html', {'gasto': gasto})