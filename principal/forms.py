
from django import forms
from areas.models import AreaComun
from empresas.models import Empresa
from locales.models import LocalComercial
from .models import Aviso, TemaGeneral, VisitanteAcceso
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User



class VisitanteLoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


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


#valida al hacer login un usuario operativo, si la empresa es suspendida o cancelada, no permite el acceso y muestra un mensaje de error
class EmpresaAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        # Mantiene la validación estándar de Django (usuario inactivo, etc.)
        super().confirm_login_allowed(user)

        if user.is_superuser:
            return  # los superusuarios no dependen de ninguna empresa

        perfil = getattr(user, 'perfilusuario', None)
        empresa = getattr(perfil, 'empresa', None) if perfil else None

        if empresa and empresa.estado in ('suspendida', 'cancelada'):
            raise forms.ValidationError(
                "Tu cuenta está %(estado)s. Por favor comunícate con el administrador del sistema: "
                "adminsoftheron@gesacadmin.com o por WhatsApp al 55 4882 2343.",
                code='empresa_suspendida',
                params={'estado': empresa.get_estado_display().lower()},
            )   


#################FORMULARIO PARA REGISTRAR UN NUEVO CONTADOR DE EMPRESAS###############
class ContadorForm(forms.Form):
    empresas = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.all().order_by("nombre"),
        label="Condominios / Empresas",
        widget=forms.SelectMultiple(attrs={"size": 8}),
    )
    nombre_completo = forms.CharField(max_length=150, label="Nombre completo")
    username = forms.CharField(max_length=150, label="Usuario")
    email = forms.EmailField(label="Correo electrónico")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ese correo ya está registrado.")
        return email


#editar empresas asignadas a un contador
class EditarContadorForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")
    empresas = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.all().order_by("nombre"),
        label="Condominios / Empresas",
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )