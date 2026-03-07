from django.shortcuts import render, redirect
from .forms import EstadoCuentaForm
from .models import EstadoCuenta, MovimientoBancario
import csv
import io
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
# Si quieres procesar PDF, instala pdfplumber y agrégalo aquí

def cargar_estado_cuenta(request):
    if request.method == 'POST':
        form = EstadoCuentaForm(request.POST, request.FILES)
        if form.is_valid():
            estado = form.save(commit=False)
            estado.empresa = request.user.empresa  # Toma la empresa del usuario firmado
            estado.save()
            archivo = request.FILES['archivo']
            if archivo.name.endswith('.csv'):
                data = archivo.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(data))
                for row in reader:
                    MovimientoBancario.objects.create(
                        estado_cuenta=estado,
                        fecha=row['fecha'],
                        descripcion=row['descripcion'],
                        importe=row['importe'],
                        tipo=row['tipo'].lower(),  # 'cargo' o 'abono'
                    )
            # Aquí puedes agregar lógica para PDF
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