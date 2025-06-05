
from decimal import Decimal
from pyexpat.errors import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
#from empresas.models import Empresa
from .models import LocalComercial
from .forms import LocalComercialForm
#from principal.models import PerfilUsuario  # si usas perfil para la empresa
#from django.shortcuts import get_object_or_404
#from django.contrib.admin.views.decorators import staff_member_required


# Create your views here.

@login_required
def lista_locales(request):
    user = request.user
    if user.is_superuser:
        #locales = LocalComercial.objects.all()
        locales = LocalComercial.objects.filter(activo=True)
    else:
        #empresa = getattr(request.user.perfilusuario, 'empresa', None)
        empresa = user.perfilusuario.empresa
        locales = LocalComercial.objects.filter(empresa=empresa, activo=True)
    return render(request, 'locales/lista_locales.html', {'locales': locales})

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
                #if perfil and perfil.empresa:
                local.empresa = perfil.empresa
                
            #local.save()
                #else:
                    #return render(request, 'error.html', {'mensaje': 'No tienes empresa asignada.'})
                local.save()
                return redirect('lista_locales')
        
    else:
        
        form = LocalComercialForm(user=user)
        # Si no es superusuario, asignamos la empresa inicial al form
        if not user.is_superuser and perfil and perfil.empresa:
            form.fields['empresa'].initial = perfil.empresa

    return render(request, 'locales/crear_local.html', {'form': form})

@login_required
def editar_local(request, pk):
    user = request.user
    local= get_object_or_404(LocalComercial, pk=pk)
    #perfil = getattr(user, 'perfilusuario', None)
    # Filtrar el local según permisos
    if not user.is_superuser and local.empresa != user.perfilusuario.empresa:
        return redirect('lista_locales')
    #if user.is_superuser:
        #local = get_object_or_404(LocalComercial, pk=pk)
    #else:
     #   local = get_object_or_404(LocalComercial, pk=pk, empresa=perfil.empresa)

    if request.method == 'POST':
        form = LocalComercialForm(request.POST, instance=local, user=user)
        if form.is_valid():
            local = form.save(commit=False)
            form.save()
            #if not user.is_superuser:
             #   local.empresa = perfil.empresa  # reforzar seguridad
            #local.save()
            return redirect('lista_locales')
    else:
        form = LocalComercialForm(instance=local, user=user)

    return render(request, 'locales/editar_local.html', {'form': form, 'local': local})

@login_required
def eliminar_local(request, pk):
    user = request.user
    local= get_object_or_404(LocalComercial, pk=pk)
    if not user.is_superuser and local.empresa != user.perfilusuario.empresa:
        return redirect('lista_locales')
    #perfil = getattr(user, 'perfilusuario', None)

    #if user.is_superuser:
     #   local = get_object_or_404(LocalComercial, pk=pk)
    #else:
     #   local = get_object_or_404(LocalComercial, pk=pk, empresa=perfil.empresa)

    if request.method == 'POST':
        #local.delete()
        local.activo = False
        local.save()
        return redirect('lista_locales')

    return render(request, 'locales/eliminar_local.html', {'local': local})

#@staff_member_required
@user_passes_test(lambda u: u.is_staff)
def locales_inactivos(request):
    locales = LocalComercial.objects.filter(activo=False)
    return render(request, 'locales/locales_inactivos.html', {'locales': locales})

#@staff_member_required
@user_passes_test(lambda u: u.is_staff)
def reactivar_local(request, pk):
    local = get_object_or_404(LocalComercial, pk=pk, activo=False)

    if request.method == 'POST':
        local.activo = True
        local.save()
        return redirect('locales_inactivos')

    return render(request, 'locales/reactivar_confirmacion.html', {'local': local})

@login_required
def incrementar_cuotas_locales(request):
    if request.method == 'POST':
        porcentaje = request.POST.get('porcentaje')
        try:
            porcentaje = Decimal(porcentaje)
            empresa = None
            if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
                empresa = request.user.perfilusuario.empresa
                locales = LocalComercial.objects.filter(empresa=empresa, activo=True)
            else:
                locales = LocalComercial.objects.filter(activo=True)

            for local in locales:
                cuota_anterior = local.cuota
                incremento = cuota_anterior * (porcentaje / Decimal('100'))
                local.cuota += incremento
                local.save()

            messages.success(request, f'Se incrementaron las cuotas en un {porcentaje}% para todos los locales activos.')
            return redirect('lista_locales')
        except:
            messages.error(request, 'Porcentaje inválido.')
    
    return render(request, 'locales/incrementar_cuotas.html')
