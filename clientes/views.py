
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cliente
from .forms import ClienteForm

@login_required
def lista_clientes(request):
    if request.user.is_superuser:
        clientes = Cliente.objects.filter(activo=True)
    else:
        empresa = request.user.perfilusuario.empresa
        clientes = Cliente.objects.filter(empresa=empresa, activo=True)
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})

@login_required
def crear_cliente(request):
    perfil = getattr(request.user, 'perfilusuario', None)

    if request.method == 'POST':
        form = ClienteForm(request.POST, user=request.user)
        if form.is_valid():
            cliente = form.save(commit=False)
            if not request.user.is_superuser and perfil:
                cliente.empresa = perfil.empresa
            cliente.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(user=request.user)
        if perfil:
            form.fields['empresa'].initial = perfil.empresa

    return render(request, 'clientes/crear_cliente.html', {'form': form})

@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if not request.user.is_superuser and cliente.empresa != request.user.perfilusuario.empresa:
        return redirect('lista_clientes')

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente, user=request.user)

    return render(request, 'clientes/editar_cliente.html', {'form': form, 'cliente': cliente})

@login_required
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if not request.user.is_superuser and cliente.empresa != request.user.perfilusuario.empresa:
        return redirect('lista_clientes')

    if request.method == 'POST':
        cliente.activo = False
        cliente.save()
        return redirect('lista_clientes')

    return render(request, 'clientes/eliminar_cliente.html', {'cliente': cliente})
