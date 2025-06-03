from django import forms
from .models import LocalComercial

class LocalComercialForm(forms.ModelForm):
    class Meta:
        model = LocalComercial
        fields = ['numero', 'ubicacion', 'superficie_m2', 'cuota', 'status', 'empresa', 'cliente', 'observaciones']
        labels = {
            'numero': 'Número del Local',
            'ubicacion': 'Ubicación',
            'superficie_m2': 'Superficie (m²)',
            'cuota': 'Cuota Mensual',
            'status': 'Estado',
            'empresa': 'Empresa',
            'cliente': 'Cliente',
            'observaciones': 'Observaciones',
        }
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del local'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicación del local'}),
            'superficie_m2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Superficie en m²'}),
            'cuota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cuota mensual'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones'}),

        }