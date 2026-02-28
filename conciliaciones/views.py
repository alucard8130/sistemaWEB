from pyexpat.errors import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django import forms
from .models import EstadoCuentaBancario


# Create your views here.
# conciliación bancaria
@login_required

class EstadoCuentaUploadForm(forms.ModelForm):
    class Meta:
        model = EstadoCuentaBancario
        fields = ['empresa', 'archivo']

def subir_estado_cuenta(request):
    if request.method == 'POST':
        form = EstadoCuentaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            estado_cuenta = form.save(commit=False)
            # El procesamiento y llenado de datos se hará después
            estado_cuenta.save()
            messages.success(request, "Archivo subido correctamente. Procesando datos...")
            # Redirige a la vista de procesamiento
            return redirect('procesar_estado_cuenta', estado_cuenta_id=estado_cuenta.id)
    else:
        form = EstadoCuentaUploadForm(request.GET)
    return render(request, 'conciliaciones/subir_estado_cuenta.html', {'form': form})


@login_required
def descargar_plantilla_estado_cuenta(request):
    contenido = (
        "fecha,cargo,abono,descripcion\n"
        "01/10/2025,0,1500.00,Pago cuota octubre\n"
        "02/10/2025,500.00,0,Pago gasto limpieza\n"
        "03/10/2025,0,2000.00,Fondeo caja chica\n"
        "04/10/2025,0,1200.00,Pago otros ingresos\n"
    )
    response = HttpResponse(contenido, content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=plantilla_estado_cuenta.csv"
    return response