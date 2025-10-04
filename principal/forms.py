
from django import forms

class VisitanteLoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

from .models import TemaGeneral

class TemaGeneralForm(forms.ModelForm):
    correos = forms.CharField(
        label="Correos destinatarios (separados por coma)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'correo1@dominio.com, correo2@dominio.com'
        }),
        help_text="Ejemplo: correo1@dominio.com, correo2@dominio.com"
    )

    class Meta:
        model = TemaGeneral
        fields = ['titulo', 'descripcion']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del asunto'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el asunto a votar'
            }),
        }    