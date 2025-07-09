from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        #exclude = ['empresa','fecha_creacion', 'fecha_actualizacion']
        fields = ['empresa','nombre', 'rfc', 'telefono', 'email', 'direccion', 'activo']
        #fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Si el usuario NO es superuser, oculta el campo empresa
        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()        

        self.fields['empresa'].required = False

        # Aplicar Bootstrap a cada campo
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, (forms.TextInput, forms.Select, forms.EmailInput, forms.Textarea)):
                widget.attrs['class'] = 'form-control'