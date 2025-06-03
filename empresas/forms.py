from django import forms
from .models import Empresa

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre', 'rfc', 'direccion', 'telefono', 'email']
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }
