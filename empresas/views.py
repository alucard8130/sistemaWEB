
#from pyexpat.errors import messages

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import CuentaBancaria,  Empresa
from .forms import CuentaBancariaForm, EmpresaForm
from django.contrib.auth.decorators import user_passes_test
from django.db.models import ProtectedError
from django.contrib import messages




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
        empresas = Empresa.objects.prefetch_related('cuentas_bancarias').all()
    else:
        empresa = getattr(request.user.perfilusuario, 'empresa', None)
        empresas = Empresa.objects.prefetch_related('cuentas_bancarias').filter(pk=empresa.pk) if empresa else Empresa.objects.none()
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
    empresa = request.user.perfilusuario.empresa  # Ajusta según tu modelo de perfil
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
def cuenta_bancaria_eliminar(request, pk):
    cuenta = get_object_or_404(CuentaBancaria, pk=pk)
    if request.method == 'POST':
        try:
            cuenta.delete()
            messages.success(request, "Cuenta bancaria eliminada correctamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar esta cuenta bancaria, tiene registros asociados.")

        return redirect('cuentas_bancarias_lista')
    return render(request, 'empresas/cuenta_bancaria_eliminar.html', {'cuenta': cuenta})



@login_required
def cuenta_bancaria_editar(request, pk):
    cuenta = get_object_or_404(CuentaBancaria, pk=pk)
    # Seguridad: solo puede editar cuentas de su propia empresa
    if not request.user.is_superuser and cuenta.empresa != request.user.perfilusuario.empresa:
        messages.error(request, "No tienes permiso para editar esta cuenta.")
        return redirect('cuentas_bancarias_lista')

    if request.method == 'POST':
        form = CuentaBancariaForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cuenta {cuenta.banco} actualizada correctamente.")
            return redirect('cuentas_bancarias_lista')
    else:
        form = CuentaBancariaForm(instance=cuenta)

    return render(request, 'empresas/cuenta_bancaria_editar.html', {
        'form': form,
        'cuenta': cuenta,
        'empresa': cuenta.empresa,
    })
