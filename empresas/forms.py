from django import forms
from .models import Empresa

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre', 'rfc', 'direccion', 'telefono', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa'
            }),
            'rfc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RFC'
            }),
            'direccion': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Dirección'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
        }
        labels = {
            'nombre': 'Nombre de la empresa',
            'rfc': 'RFC',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'email': 'Email',
        }
