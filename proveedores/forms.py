from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        exclude = ['fecha_creacion', 'fecha_actualizacion']
        fields = ['empresa', 'nombre', 'rfc', 'telefono', 'email', 'direccion', 'activo']

def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Si el usuario NO es superuser, oculta el campo empresa
        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()        

