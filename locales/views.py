
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from empresas.models import Empresa
from .models import LocalComercial
from .forms import LocalComercialForm
from principal.models import PerfilUsuario  # si usas perfil para la empresa
from django.shortcuts import get_object_or_404


# Create your views here.
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from .forms import LocalComercialForm
from .models import LocalComercial
from empresas.models import Empresa
from principal.models import PerfilUsuario

@login_required
def crear_local(request):
    user = request.user
    perfil = getattr(user, 'perfilusuario', None)
    
    if request.method == 'POST':
        #form = LocalComercialForm(request.POST, user=user)
        form = LocalComercialForm(request.POST or None, user=request.user)

        if form.is_valid():
            local = form.save(commit=False)

            # Si no es superusuario, asignamos su empresa
            if not user.is_superuser:
                if perfil and perfil.empresa:
                    local.empresa = perfil.empresa
                else:
                    return render(request, 'error.html', {'mensaje': 'No tienes empresa asignada.'})

            local.save()
            return redirect('lista_locales')
    else:
        form = LocalComercialForm(user=user)

        # Si no es superusuario, asignamos la empresa inicial al form
        if not user.is_superuser and perfil and perfil.empresa:
            form.fields['empresa'].initial = perfil.empresa

    return render(request, 'locales/crear_local.html', {'form': form})


"""@login_required
def crear_local(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = LocalComercialForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('lista_locales')
        else:
            form = LocalComercialForm()
    else:
        perfil = getattr(request.user, 'perfilusuario', None)
        if not perfil or not perfil.empresa:
            return render(request, 'error.html', {'mensaje': 'No tienes empresa asignada.'})

        if request.method == 'POST':
            form = LocalComercialForm(request.POST)
            if form.is_valid():
                local = form.save(commit=False)
                local.empresa = perfil.empresa
                local.save()
                return redirect('lista_locales')
        else:
            form = LocalComercialForm()
    return render(request, 'locales/crear_local.html', {'form': form})"""



"""@login_required
def crear_local(request):
    if request.user.is_superuser:
        empresa = None
    else:
        empresa = getattr(request.user.perfilusuario, 'empresa', None)

    if request.method == 'POST':
        form = LocalComercialForm(request.POST)
        if form.is_valid():
            local = form.save(commit=False)
            local.empresa = empresa if empresa else Empresa.objects.first()  # opcional
            local.save()
            return redirect('lista_locales')
    else:
        form = LocalComercialForm()
    return render(request, 'locales/crear_local.html', {'form': form})"""

@login_required
def lista_locales(request):
    if request.user.is_superuser:
        locales = LocalComercial.objects.all()
    else:
        empresa = getattr(request.user.perfilusuario, 'empresa', None)
        locales = LocalComercial.objects.filter(empresa=empresa)
    return render(request, 'locales/lista_locales.html', {'locales': locales})


@login_required
def editar_local(request, pk):
    user = request.user
    perfil = getattr(user, 'perfilusuario', None)

    # Filtrar el local según permisos
    if user.is_superuser:
        local = get_object_or_404(LocalComercial, pk=pk)
    else:
        local = get_object_or_404(LocalComercial, pk=pk, empresa=perfil.empresa)

    if request.method == 'POST':
        form = LocalComercialForm(request.POST, instance=local, user=user)
        if form.is_valid():
            local = form.save(commit=False)
            if not user.is_superuser:
                local.empresa = perfil.empresa  # reforzar seguridad
            local.save()
            return redirect('lista_locales')
    else:
        form = LocalComercialForm(instance=local, user=user)

    return render(request, 'locales/editar_local.html', {'form': form, 'local': local})

@login_required
def eliminar_local(request, pk):
    user = request.user
    perfil = getattr(user, 'perfilusuario', None)

    if user.is_superuser:
        local = get_object_or_404(LocalComercial, pk=pk)
    else:
        local = get_object_or_404(LocalComercial, pk=pk, empresa=perfil.empresa)

    if request.method == 'POST':
        local.delete()
        return redirect('lista_locales')

    return render(request, 'locales/eliminar_local.html', {'local': local})
