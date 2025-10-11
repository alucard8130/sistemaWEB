from django import forms
from .models import Empresa

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'nombre',
            'rfc',
            'regimen_fiscal',
            'codigo_postal',
            'cuenta_bancaria',
            'numero_cuenta',
            'saldo_inicial',
            'saldo_final',
            'direccion',
            'telefono',
            'email'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa'
            }),
            'rfc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RFC'
            }),
            'regimen_fiscal': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Régimen Fiscal'
            }),
            'direccion': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Dirección'
            }),
            'codigo_postal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Postal'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'cuenta_bancaria': forms.Select(attrs={
                'class': 'form-control',
            }),
            'numero_cuenta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de Cuenta'
            }),
            'saldo_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Saldo Inicial'
            }),
            'saldo_final': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Saldo Final'
            }),
        }
        labels = {
            'nombre': 'Nombre de la empresa',
            'rfc': 'RFC',
            'regimen_fiscal': 'Régimen Fiscal',
            'codigo_postal': 'Código Postal',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'email': 'Email',
            'cuenta_bancaria': 'Banco',
            'numero_cuenta': 'Número de Cuenta',
            'saldo_inicial': 'Saldo Inicial',
            'saldo_final': 'Saldo Final',
        }
