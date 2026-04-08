from decimal import Decimal

from django.shortcuts import render, redirect

from clientes.models import Cliente
from facturacion.models import Factura
from .forms import EstadoCuentaForm
from .models import EstadoCuenta, MovimientoBancario
import csv
import io
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

def cargar_estado_cuenta(request):
    if request.method == 'POST':
        form = EstadoCuentaForm(request.POST, request.FILES)
        if form.is_valid():
            estado = form.save(commit=False)
            estado.empresa = request.user.empresa
            estado.save()
            archivo = request.FILES['archivo']
            if archivo.name.endswith('.csv'):
                data = archivo.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(data))
                for row in reader:
                    descripcion = row['descripcion']
                    monto_restante = Decimal(row['importe'])
                    cliente = None

                    # Buscar referencia de pago en la descripción
                    for c in Cliente.objects.exclude(referencia_pago__isnull=True).exclude(referencia_pago__exact=''):
                        if c.referencia_pago and c.referencia_pago in descripcion:
                            cliente = c
                            break

                    if cliente:
                        facturas = Factura.objects.filter(cliente=cliente, pagada=False).order_by('fecha')
                        for factura in facturas:
                            saldo_factura = factura.total - factura.pagado  # Ajusta según tus campos
                            if monto_restante <= 0:
                                break
                            pago = min(monto_restante, saldo_factura)
                            # Registrar el movimiento bancario asociado a la factura
                            MovimientoBancario.objects.create(
                                estado_cuenta=estado,
                                fecha=row['fecha'],
                                descripcion=descripcion,
                                importe=pago,
                                tipo=row['tipo'].lower(),
                                factura=factura,
                                identificado=True,
                            )
                            factura.pagado += pago  # Ajusta según tu modelo
                            if factura.pagado >= factura.total:
                                factura.pagada = True
                            factura.save()
                            monto_restante -= pago

                        # Si sobra saldo, va a depósito por identificar
                        if monto_restante > 0:
                            MovimientoBancario.objects.create(
                                estado_cuenta=estado,
                                fecha=row['fecha'],
                                descripcion=descripcion + " (Depósito por identificar)",
                                importe=monto_restante,
                                tipo=row['tipo'].lower(),
                                identificado=False,
                            )
                    else:
                        # No se encontró cliente, todo el monto va a depósito por identificar
                        MovimientoBancario.objects.create(
                            estado_cuenta=estado,
                            fecha=row['fecha'],
                            descripcion=descripcion,
                            importe=row['importe'],
                            tipo=row['tipo'].lower(),
                            identificado=False,
                        )
            return redirect('conciliacion:lista_movimientos', estado_id=estado.id)
    else:
        form = EstadoCuentaForm()
    return render(request, 'conciliacion/cargar_estado_cuenta.html', {'form': form})


def lista_movimientos(request, estado_id):
    estado = get_object_or_404(EstadoCuenta, id=estado_id)
    movimientos = estado.movimientos.all()
    return render(request, 'conciliacion/lista_movimientos.html', {'estado': estado, 'movimientos': movimientos})

@require_POST
def no_identificar(request, mov_id):
    mov = get_object_or_404(MovimientoBancario, id=mov_id)
    mov.deposito_por_identificar = True
    mov.save()
    return redirect('conciliaciones:lista_movimientos', estado_id=mov.estado_cuenta.id)