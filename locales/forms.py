from django import forms
from clientes.models import Cliente
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

        #self.fields['cliente'].queryset = Cliente.objects.all().order_by('nombre')

        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            empresa = user.perfilusuario.empresa
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
        else:
            self.fields['cliente'].queryset = Cliente.objects.all()


            # Si no es superusuario, ocultamos el campo empresa
        #if user is not None and not user.is_superuser:
         #   self.fields['empresa'].widget = forms.HiddenInput()
          #  if hasattr(user, 'empresa'):
           #     self.fields['cliente'].queryset = Cliente.objects.filter(empresa=user.empresa)
            #else:
             #   self.fields['cliente'].queryset = Cliente.objects.none()
        #else:
         #   self.fields['cliente'].queryset = Cliente.objects.all()

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
