from django import forms
from .models import CorteEstacionamiento
from empresas.models import CuentaBancaria


class CorteEstacionamientoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        if empresa:
            self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.filter(
                empresa=empresa, activa=True
            )
        else:
            self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.filter(activa=True)

        # Mostrar/ocultar campos de operador según checkbox
        self.fields['nombre_operador'].required = False
        self.fields['porcentaje_operador'].required = False
        self.fields['monto_renta_operador'].required = False

    class Meta:
        model = CorteEstacionamiento
        fields = [
            'periodo', 'fecha_inicio', 'fecha_fin',
            'total_efectivo', 'total_tarjeta', 'total_boletos',
            'tiene_operador_externo', 'nombre_operador',
            'porcentaje_operador', 'monto_renta_operador',
            'fecha_deposito',
            'cuenta_bancaria', 'observaciones', 'archivo_origen',
        ]
        widgets = {
            'periodo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'total_efectivo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'total_tarjeta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'total_boletos': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'tiene_operador_externo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tiene_operador'}),
            'nombre_operador': forms.TextInput(attrs={'class': 'form-control'}),
            'porcentaje_operador': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'monto_renta_operador': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'cuenta_bancaria': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'archivo_origen': forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx,.xls'}),
            'fecha_deposito': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'periodo': 'Tipo de corte',
            'fecha_inicio': 'Fecha inicio',
            'fecha_fin': 'Fecha fin',
            'total_efectivo': 'Total efectivo',
            'total_tarjeta': 'Total Tarjeta/SPEI',
            'total_boletos': 'Número de boletos',
            'tiene_operador_externo': '¿Tiene operador externo?',
            'nombre_operador': 'Nombre del operador',
            'porcentaje_operador': '% que corresponde al operador',
            'monto_renta_operador': 'Renta fija del operador',
            'cuenta_bancaria': 'Cuenta bancaria donde se depositó',
            'observaciones': 'Observaciones',
            'archivo_origen': 'Archivo del sistema de estacionamiento (opcional)',
            'fecha_deposito': 'Fecha de depósito en banco',
        }


class ImportarTicketsForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo CSV',
        help_text='El archivo debe tener columnas: numero_ticket, fecha, hora_entrada, hora_salida, minutos, monto, forma_pago',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )