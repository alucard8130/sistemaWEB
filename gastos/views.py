
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
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
    if request.user.is_superuser:
        gastos = Gasto.objects.all().select_related('empresa', 'proveedor', 'empleado', 'tipo_gasto')
    else:
        gastos = Gasto.objects.filter(empresa=request.user.perfilusuario.empresa)
    return render(request, 'gastos/lista.html', {'gastos': gastos})

@login_required
def gasto_nuevo(request):
    if request.method == 'POST':
        form = GastoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            gasto = form.save(commit=False)
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
        form = GastoForm(request.POST, request.FILES, instance=gasto, user=request.user)
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