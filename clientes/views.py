
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from empresas.models import Empresa
from .models import Cliente
from .forms import ClienteForm
from django.contrib.admin.views.decorators import staff_member_required
import openpyxl
from django.contrib import messages

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

@staff_member_required
def carga_masiva_clientes(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        wb = openpyxl.load_workbook(archivo)
        hoja = wb.active

        insertados = 0
        duplicados = 0
        errores = 0

        for fila in hoja.iter_rows(min_row=2, values_only=True):
            nombre, rfc, telefono, email, empresa_nombre = fila

            try:
                empresa = Empresa.objects.get(nombre__iexact=empresa_nombre)
                existe = Cliente.objects.filter(nombre=nombre, empresa=empresa, activo=True).exists()

                if existe:
                    duplicados += 1
                else:
                    Cliente.objects.create(
                        nombre=nombre,
                        rfc=rfc,
                        telefono=telefono,
                        email=email,
                        empresa=empresa
                    )
                    insertados += 1
            except Exception:
                errores += 1
                continue

        messages.success(request, f"Insertados: {insertados}, Duplicados: {duplicados}, Errores: {errores}")
        return redirect('lista_clientes')

    return render(request, 'clientes/carga_masiva_clientes.html')