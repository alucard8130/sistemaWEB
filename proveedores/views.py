
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from empresas.models import Empresa
from .forms import ProveedorForm
from .models import Proveedor
from django import forms

@login_required
def proveedor_crear(request):
    if request.method == 'POST':
        post = request.POST.copy()
        if not request.user.is_superuser:
            post['empresa'] = request.user.perfilusuario.empresa.id  
        form = ProveedorForm(post, user=request.user)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.empresa = request.user.perfilusuario.empresa
            proveedor.save()
            return redirect('proveedor_lista')
    else:
        form = ProveedorForm(user=request.user)
        if not request.user.is_superuser and 'empresa' in form.fields:
            form.fields['empresa'].initial = request.user.perfilusuario.empresa
    return render(request, 'proveedores/crear_proveedor.html', {'form': form})

@login_required
def proveedor_lista(request):
    if request.user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            proveedores = Proveedor.objects.filter(empresa_id=empresa_id, activo=True)
        else:
            proveedores = Proveedor.objects.filter(activo=True)
    else:
        empresa = request.user.perfilusuario.empresa
        proveedores = Proveedor.objects.filter(empresa=empresa, activo=True)
    return render(request, 'proveedores/lista.html', {'proveedores': proveedores})

@login_required
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    # Solo el superusuario o usuarios de la empresa pueden editar
    if not request.user.is_superuser and proveedor.empresa != request.user.perfilusuario.empresa:
        return redirect('proveedor_lista')

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('proveedor_lista')
    else:
        form = ProveedorForm(instance=proveedor, user=request.user)
    return render(request, 'proveedores/editar.html', {'form': form, 'proveedor': proveedor})
