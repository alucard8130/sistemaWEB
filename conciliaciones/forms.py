
from django import forms
from .models import EstadoCuenta

class EstadoCuentaForm(forms.ModelForm):
    class Meta:
        model = EstadoCuenta
        fields = ['periodo', 'archivo']