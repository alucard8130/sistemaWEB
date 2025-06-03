
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Empresa
from .forms import EmpresaForm


# Create your views here.
@login_required
def empresa_crear(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('empresa_lista')
    else:
        form = EmpresaForm()
    return render(request, 'empresas/crear.html', {'form': form})

@login_required
def empresa_lista(request):
    empresas = Empresa.objects.all()
    return render(request, 'empresas/lista.html', {'empresas': empresas})

@login_required
def empresa_editar(request, pk):
    empresa = Empresa.objects.get(pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            return redirect('empresa_lista')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'empresas/editar.html', {'form': form, 'empresa': empresa})

@login_required
def empresa_eliminar(request, pk):
    empresa = Empresa.objects.get(pk=pk)
    if request.method == 'POST':
        empresa.delete()
        return redirect('empresa_lista')
    return render(request, 'empresas/eliminar.html', {'empresa': empresa})
