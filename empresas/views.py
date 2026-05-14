
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import CuentaBancaria, CuentaBancaria, Empresa
from .forms import CuentaBancariaForm, EmpresaForm
from django.contrib.auth.decorators import user_passes_test


# Create your views here.
#@login_required
@user_passes_test(lambda u: u.is_superuser)
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
    if request.user.is_superuser:
        empresas = Empresa.objects.all()
    else:
        empresa = getattr(request.user.perfilusuario, 'empresa', None)
        empresas = Empresa.objects.filter(pk=empresa.pk) if empresa else Empresa.objects.none()
    return render(request, 'empresas/lista.html', {'empresas': empresas})


@login_required
def empresa_editar(request, pk):
    empresa = Empresa.objects.get(pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        print(form.errors)  # Esto mostrará los errores en la consola
        if form.is_valid():
            form.save()
            return redirect('empresa_lista')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'empresas/editar.html', {'form': form, 'empresa': empresa})

#@login_required
@user_passes_test(lambda u: u.is_superuser)
def empresa_eliminar(request, pk):
    empresa = Empresa.objects.get(pk=pk)
    if request.method == 'POST':
        empresa.delete()
        return redirect('empresa_lista')
    return render(request, 'empresas/eliminar.html', {'empresa': empresa})


############################
# Vistas para cuentas bancarias
@login_required
def cuenta_bancaria_crear(request):
    #empresa = Empresa.objects.get(pk=empresa_pk)
    empresa = request.user.perfilusuario.empresa  # Ajusta según tu modelo de perfil
    #empresa = get_object_or_404(Empresa, id=empresa_id)
    if request.method == 'POST':
        form = CuentaBancariaForm(request.POST)
        if form.is_valid():
            cuenta = form.save(commit=False)
            cuenta.empresa = empresa
            cuenta.save()
            return redirect('cuentas_bancarias_lista')
    else:
        form = CuentaBancariaForm()
    return render(request, 'empresas/cuenta_bancaria_crear.html', {'form': form, 'empresa': empresa})

@login_required
def cuentas_bancarias_lista(request):
    empresa = request.user.perfilusuario.empresa  # Ajusta según tu modelo de perfil
    cuentas = CuentaBancaria.objects.filter(empresa=empresa)
    return render(request, 'empresas/cuentas_bancarias_lista.html', {'cuentas': cuentas, 'empresa': empresa})

@login_required
# def cuenta_bancaria_editar(request, pk):
#     cuenta = get_object_or_404(CuentaBancaria, pk=pk)
#     if request.method == 'POST':
#         form = CuentaBancariaForm(request.POST, instance=cuenta)
#         if form.is_valid():
#             form.save()
#             return redirect('cuentas_bancarias_lista')
#     else:
#         form = CuentaBancariaForm(instance=cuenta)
#     return render(request, 'empresas/cuenta_bancaria_editar.html', {'form': form, 'cuenta': cuenta})

@login_required
def cuenta_bancaria_eliminar(request, pk):
    cuenta = get_object_or_404(CuentaBancaria, pk=pk)
    if request.method == 'POST':
        cuenta.delete()
        return redirect('cuentas_bancarias_lista')
    return render(request, 'empresas/cuenta_bancaria_eliminar.html', {'cuenta': cuenta})