from django import forms
from .models import LocalComercial
from empresas.models import Empresa

class LocalComercialForm(forms.ModelForm):
    class Meta:
        model = LocalComercial
        #exclude = ['empresa']  # será asignada desde la vista para usuarios normales
        fields = ['numero', 'cliente','empresa', 'superficie_m2', 'cuota','ubicacion', 'status', 'observaciones']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # obtenemos el usuario desde la vista
        super().__init__(*args, **kwargs)
    
            # Si no es superusuario, ocultamos el campo empresa
        if user is not None and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        numero = cleaned_data.get('numero')
        empresa = cleaned_data.get('empresa')

        if numero and empresa:
            # Buscar duplicado activo
            duplicado = LocalComercial.objects.filter(numero=numero, empresa=empresa).exclude(pk=self.instance.pk)
            if duplicado.exists():
                raise forms.ValidationError(f"Ya existe un local con número '{numero}' en esta empresa.")
        return cleaned_data

    """labels = {
        'numero': 'Número del Local',
        'ubicacion': 'Ubicación',
        'superficie_m2': 'Superficie (m²)',
        'cuota': 'Cuota Mensual',
        'status': 'Estado',
        'empresa': 'Empresa',
        'cliente': 'Cliente',
        'observaciones': 'Observaciones',
    }
    widgets = {
        'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numero del local'}),
        'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicación del local'}),
        'superficie_m2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Superficie en m²'}),
        'cuota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cuota mensual'}),
        'status': forms.Select(attrs={'class': 'form-control'}),
        'empresa': forms.Select(attrs={'class': 'form-control'}),
        'cliente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
        'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones'}),

    }"""
    
       