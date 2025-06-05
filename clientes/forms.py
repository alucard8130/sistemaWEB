from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['empresa','nombre', 'rfc', 'telefono', 'email', 'activo']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        empresa = cleaned_data.get('empresa')
        rfc= cleaned_data.get('rfc')

        if rfc and empresa:
            qs = Cliente.objects.filter(rfc__iexact=rfc, empresa=empresa).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ya existe un cliente con ese RFC en esta empresa.")
        return cleaned_data


class ClienteCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label='Archivo Excel (.xlsx)')

