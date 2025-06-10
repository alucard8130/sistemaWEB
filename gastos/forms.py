from django import forms
from .models import SubgrupoGasto, TipoGasto

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