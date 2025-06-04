
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import AreaComun
from .forms import AreaComunForm

@login_required
def lista_areas(request):
    user = request.user
    if user.is_superuser:
        areas = AreaComun.objects.filter(activo=True)
    else:
        empresa = user.perfilusuario.empresa
        areas = AreaComun.objects.filter(empresa=empresa, activo=True)
    return render(request, 'areas/lista_areas.html', {'areas': areas})

@login_required
def crear_area(request):
    user = request.user
    perfil = getattr(user, 'perfilusuario', None)

    if request.method == 'POST':
        form = AreaComunForm(request.POST, user=user)
        if form.is_valid():
            area = form.save(commit=False)
            if not user.is_superuser:
                area.empresa = perfil.empresa
            area.save()
            return redirect('lista_areas')
    else:
        form = AreaComunForm(user=user)
        if not user.is_superuser and perfil and perfil.empresa:
            form.fields['empresa'].initial = perfil.empresa

    return render(request, 'areas/crear_area.html', {'form': form})

@login_required
def editar_area(request, pk):
    user = request.user
    area = get_object_or_404(AreaComun, pk=pk)
    if not user.is_superuser and area.empresa != user.perfilusuario.empresa:
        return redirect('lista_areas')

    if request.method == 'POST':
        form = AreaComunForm(request.POST, instance=area, user=user)
        if form.is_valid():
            form.save()
            return redirect('lista_areas')
    else:
        form = AreaComunForm(instance=area, user=user)

    return render(request, 'areas/editar_area.html', {'form': form, 'area': area})

@login_required
def eliminar_area(request, pk):
    user = request.user
    area = get_object_or_404(AreaComun, pk=pk)
    if not user.is_superuser and area.empresa != user.perfilusuario.empresa:
        return redirect('lista_areas')

    if request.method == 'POST':
        area.activo = False
        area.save()
        return redirect('lista_areas')

    return render(request, 'areas/eliminar_area.html', {'area': area})

@user_passes_test(lambda u: u.is_staff)
def areas_inactivas(request):
    areas = AreaComun.objects.filter(activo=False)
    return render(request, 'areas/areas_inactivas.html', {'areas': areas})

@user_passes_test(lambda u: u.is_staff)
def reactivar_area(request, pk):
    area = get_object_or_404(AreaComun, pk=pk, activo=False)

    if request.method == 'POST':
        area.activo = True
        area.save()
        return redirect('areas_inactivas')

    return render(request, 'areas/reactivar_confirmacion.html', {'area': area})
