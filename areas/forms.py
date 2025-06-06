from django import forms
from .models import AreaComun
from clientes.models import Cliente
from empresas.models import Empresa


class AreaComunForm(forms.ModelForm):
    class Meta:
        model = AreaComun
        fields = ['num_contrato','numero','cliente','empresa', 'ubicacion', 'superficie_m2', 'cuota','giro','fecha_inicial', 'fecha_fin', 'status',  'observaciones']
        widgets = {
            'fecha_inicial': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        #self.user = kwargs.pop('user', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        #if not self.user.is_superuser:
         #   self.fields['empresa'].widget = forms.HiddenInput()
        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            empresa = user.perfilusuario.empresa
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
        else:
            self.fields['cliente'].queryset = Cliente.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        empresa = cleaned_data.get('empresa')

        if nombre and empresa:
            qs = AreaComun.objects.filter(nombre__iexact=nombre, empresa=empresa, activo=True)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ya existe un área común con ese nombre en esta empresa.")
        return cleaned_data

class AsignarClienteForm(forms.ModelForm):
    class Meta:
        model = AreaComun
        fields = ['cliente','fecha_inicial', 'fecha_fin']
        widgets = {
            'fecha_inicial': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get('cliente')
        fecha_inicial = cleaned_data.get('fecha_inicial')
        fecha_fin = cleaned_data.get('fecha_fin')

        if not cliente:
            self.add_error('cliente', 'Debe seleccionar un cliente.')
        if not fecha_inicial:
            self.add_error('fecha_inicial', 'Debe ingresar la fecha inicial.')
        if not fecha_fin:
            self.add_error('fecha_fin', 'Debe ingresar la fecha fin.')

        return cleaned_data    

class AreaComunCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label='Archivo Excel (.xlsx)')
