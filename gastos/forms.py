from django import forms
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