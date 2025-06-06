from django import forms
from .models import Factura, Pago

class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['cliente', 'local', 'area_comun', 'fecha_vencimiento', 'monto', 'observaciones']
        widgets = {
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and not self.user.is_superuser:
            empresa = self.user.perfilusuario.empresa
            self.fields['cliente'].queryset = self.fields['cliente'].queryset.filter(empresa=empresa)
            self.fields['local'].queryset = self.fields['local'].queryset.filter(empresa=empresa)
            self.fields['area_comun'].queryset = self.fields['area_comun'].queryset.filter(empresa=empresa)
      
class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['fecha_pago', 'monto', 'forma_pago']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Monto no requerido desde el principio (el clean lo maneja)
        self.fields['monto'].required = False

    def clean(self):
        cleaned_data = super().clean()
        forma_pago = cleaned_data.get('forma_pago')
        monto = cleaned_data.get('monto')
        if forma_pago != 'nota_credito' and (monto is None or monto == 0):
            self.add_error('monto', 'El monto es obligatorio excepto para Nota de Crédito.')
        # Opcional: Si es nota de crédito, pone monto a cero
        if forma_pago == 'nota_credito':
            cleaned_data['monto'] = 0
        return cleaned_data
        
    def clean_fecha_pago(self):
        fecha_pago = self.cleaned_data['fecha_pago']
        if fecha_pago == None:
            raise forms.ValidationError("La fecha de pago es obligatoria.")
        return fecha_pago


class FacturaCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label='Archivo Excel (.xlsx)')

class FacturaEditForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['cliente', 'local', 'area_comun', 'folio', 'fecha_vencimiento', 'monto', 'estatus', 'observaciones']    