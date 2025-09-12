# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import EmpleadoForm
from .models import Empleado


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

