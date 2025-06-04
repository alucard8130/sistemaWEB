from django import forms
from .models import Factura

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
      
