
from django import forms
from areas.models import AreaComun
from empresas.models import Empresa
from locales.models import LocalComercial



class VisitanteLoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

from .models import Aviso, TemaGeneral, VisitanteAcceso

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

# principal/forms.py
class VisitanteRegistroForm(forms.ModelForm):
    nombre=forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), label="Nombre Completo", required=True)
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirmar contraseña")
    empresas = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.all(),
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label="Condominio"
    )
    locales = forms.ModelMultipleChoiceField(
        queryset=LocalComercial.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label="Locales"
    )
    areas = forms.ModelMultipleChoiceField(
        queryset=AreaComun.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label="Áreas Comunes"
    )

    def __init__(self, *args, **kwargs):
        empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        if empresa_id:
            self.fields['locales'].queryset = LocalComercial.objects.filter(empresa_id=empresa_id)
            self.fields['areas'].queryset = AreaComun.objects.filter(empresa_id=empresa_id)
        else:
            self.fields['locales'].queryset = LocalComercial.objects.none()
            self.fields['areas'].queryset = AreaComun.objects.none()

    class Meta:
        model = VisitanteAcceso
        fields = ['nombre','username', 'password','password2', 'email', 'empresas', 'locales', 'areas']
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',}
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),    
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        if password and password2 and password != password2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if VisitanteAcceso.objects.filter(username=username).exists():
            raise forms.ValidationError("El nombre de usuario ya está registrado.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if email and VisitanteAcceso.objects.filter(email=email).exists():
            raise forms.ValidationError("El correo electrónico ya está registrado.")
        return email