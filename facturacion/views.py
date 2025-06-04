
# Create your views here.
from django.shortcuts import render, redirect
from empresas.models import Empresa
from .forms import FacturaForm
from .models import Factura
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def crear_factura(request):
    if request.method == 'POST':
        form = FacturaForm(request.POST, user=request.user)
        if form.is_valid():
            factura = form.save(commit=False)
            if request.user.is_superuser:
                factura.empresa = factura.cliente.empresa
            else:
                factura.empresa = request.user.perfilusuario.empresa

            # Crear folio único
            count = Factura.objects.filter(fecha_emision__year=now().year).count() + 1
            factura.folio = f"MAN-{now().year}-{count:04d}"
            factura.save()
            messages.success(request, "Factura creada correctamente.")
            return redirect('lista_facturas')
    else:
        form = FacturaForm(user=request.user)

    return render(request, 'facturacion/crear_factura.html', {'form': form})

"""@login_required
def lista_facturas(request):
    if request.user.is_superuser:
        facturas = Factura.objects.all()
    else:
        empresa = request.user.perfilusuario.empresa
        facturas = Factura.objects.filter(empresa=empresa)

    return render(request, 'facturacion/lista_facturas.html', 
        {'facturas': facturas})
from empresas.models import Empresa"""

@login_required
def lista_facturas(request):
    empresas = Empresa.objects.all() if request.user.is_superuser else []
    empresa_id = request.GET.get('empresa')

    if request.user.is_superuser:
        if empresa_id:
            facturas = Factura.objects.filter(empresa_id=empresa_id)
        else:
            facturas = Factura.objects.all()
    else:
        empresa = request.user.perfilusuario.empresa
        facturas = Factura.objects.filter(empresa=empresa)

    return render(request, 'facturacion/lista_facturas.html', {
        'facturas': facturas,
        'empresas': empresas,
        'empresa_seleccionada': int(empresa_id) if empresa_id else None
    })
