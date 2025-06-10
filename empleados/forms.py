from django import forms
from .models import Empleado

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['empresa', 'nombre','rfc', 'puesto', 'departamento','telefono', 'email', 'activo']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()

        self.fields['empresa'].required = False