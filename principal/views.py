
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from empresas.models import Empresa
from clientes.models import Cliente
from locales.models import LocalComercial
from areas.models import AreaComun
from facturacion.models import Factura, Pago
# Create your views here.

@login_required
def bienvenida(request):
    empresa = None
    if not request.user.is_superuser:
        empresa = request.user.perfilusuario.empresa
    return render(request, 'bienvenida.html', {
        'empresa': empresa,
    })

@staff_member_required
@login_required
def reiniciar_sistema(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Orden: pagos > facturas > locales/areas > clientes > empresas
                Pago.objects.all().delete()
                Factura.objects.all().delete()
                LocalComercial.objects.all().delete()
                AreaComun.objects.all().delete()
                Cliente.objects.all().delete()
                Empresa.objects.all().delete()
            messages.success(request, '¡El sistema fue reiniciado exitosamente!')
        except Exception as e:
            messages.error(request, f'Error al reiniciar: {e}')
        return redirect('bienvenida')
    return render(request, 'reiniciar_sistema.html')