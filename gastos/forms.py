from django import forms

from empleados.models import Empleado
from proveedores.models import Proveedor
from .models import Gasto, SubgrupoGasto, TipoGasto

class SubgrupoGastoForm(forms.ModelForm):
    class Meta:
        model = SubgrupoGasto
        fields = ['grupo', 'nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'grupo': forms.Select(attrs={'class': 'form-select'}),
        }
        
class TipoGastoForm(forms.ModelForm):
    class Meta:
        model = TipoGasto
        fields = ['subgrupo', 'nombre', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows':2}),
        }

class GastoForm(forms.ModelForm):
    origen_tipo = forms.ChoiceField(choices=[('proveedor', 'Proveedor'), ('empleado', 'Empleado')],label="Tipo de origen", required=True)

 
    class Meta:
        model = Gasto
        fields = ['empresa', 'proveedor', 'empleado', 'tipo_gasto', 'descripcion', 'fecha', 'monto', 'comprobante', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows':2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Solo superusuario puede elegir empresa, los demás sólo la propia
        if not user or not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()

        self.fields['empresa'].required = False

        # Por defecto vacíos si no hay empresa
        self.fields['proveedor'].queryset = Proveedor.objects.none()
        self.fields['empleado'].queryset = Empleado.objects.none()

        if user:
            if user.is_superuser:
                # Para superusuario, se muestran todos
                self.fields['proveedor'].queryset = Proveedor.objects.all()
                self.fields['empleado'].queryset = Empleado.objects.all()
            else:
                empresa = getattr(user.perfilusuario, 'empresa', None)
                if empresa:
                    self.fields['proveedor'].queryset = Proveedor.objects.filter(empresa=empresa)
                    self.fields['empleado'].queryset = Empleado.objects.filter(empresa=empresa)
        
    #si se selecciona proveedor, empleado no es requerido y viceversa
    def clean(self):
        cleaned_data = super().clean()
        proveedor = cleaned_data.get('proveedor')
        empleado = cleaned_data.get('empleado')
        origen_tipo = cleaned_data.get('origen_tipo')

        if origen_tipo == 'proveedor' and not proveedor:
            self.add_error('proveedor', 'Debes seleccionar un proveedor.')
        if origen_tipo == 'empleado' and not empleado:
            self.add_error('empleado', 'Debes seleccionar un empleado.')
        # Opcional: si quieres que uno de los dos sea obligatorio siempre
        if not proveedor and not empleado:
            raise forms.ValidationError('Debes seleccionar un proveedor o un empleado.')
        return cleaned_data

from django import forms
from .models import PagoGasto

class PagoGastoForm(forms.ModelForm):
    class Meta:
        model = PagoGasto
        fields = ['fecha_pago', 'monto', 'forma_pago', 'referencia']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'forma_pago': forms.Select(attrs={'class': 'form-select'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }
   