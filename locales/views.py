
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from empresas.models import Empresa
from .models import LocalComercial
from .forms import LocalComercialForm
from principal.models import PerfilUsuario  # si usas perfil para la empresa


# Create your views here.
@login_required
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
    return render(request, 'locales/crear_local.html', {'form': form})

@login_required
def lista_locales(request):
    if request.user.is_superuser:
        locales = LocalComercial.objects.all()
    else:
        empresa = getattr(request.user.perfilusuario, 'empresa', None)
        locales = LocalComercial.objects.filter(empresa=empresa)
    return render(request, 'locales/lista_locales.html', {'locales': locales})
