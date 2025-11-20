from django import forms
from .models import Cliente 

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['empresa','nombre', 'rfc', 'tipo_contribuyente','regimen_fiscal','direccion_domicilio','codigo_postal','uso_cfdi','telefono', 'email', 'activo']
        widgets = {
            'empresa': forms.Select(attrs={
                'class': 'form-control'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razon Social sin AC, S.A. de C.V.'
            }),
            'rfc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RFC'
            }),
            'tipo_contribuyente': forms.Select(attrs={
                'class': 'form-control',
            }),
            'regimen_fiscal': forms.Select(attrs={
                'class': 'form-control',
            }),
            'direccion_domicilio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección del domicilio fiscal'
            }),
            'codigo_postal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Publico en general captura Codigo Postal del emisor'
            }),
            'uso_cfdi': forms.Select(attrs={
                'class': 'form-control',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
        }
        labels = {
            'rfc': 'RFC',
            'telefono': 'Teléfono',
            'codigo_postal': 'Código Postal',
            'regimen_fiscal': 'Régimen Fiscal',
        }
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            if self.instance.pk:
                self.fields['empresa'].initial = self.user.perfilusuario.empresa
            
        self.fields['regimen_fiscal'].required = True
        self.fields['uso_cfdi'].required = True
        self.fields['codigo_postal'].required = True
        self.fields['tipo_contribuyente'].required = True
        self.fields['direccion_domicilio'].required = True
    
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

