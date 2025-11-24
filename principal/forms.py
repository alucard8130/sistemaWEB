
from django import forms
from empresas.models import Empresa



class VisitanteLoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

from .models import Aviso, TemaGeneral

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

class CSDUploadForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.all(), label="Empresa")
    cer_file = forms.FileField(label="Certificado (.cer)")
    key_file = forms.FileField(label="Llave privada (.key)")
    key_password = forms.CharField(label="Contraseña de la llave", widget=forms.PasswordInput)


#modulo conciliacion bancaria
class EstadoCuentaUploadForm(forms.Form):
    archivo = forms.FileField(label="Estado de cuenta bancario (.csv)")


#Modulo avisos y recordatorios
class AvisoForm(forms.ModelForm):
    class Meta:
        model = Aviso
        fields = ['titulo', 'mensaje']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del aviso'
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe el mensaje del aviso'
            }),
        }