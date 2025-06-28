# presupuestos/forms.py
from django import forms

from empresas.models import Empresa
from .models import Presupuesto

class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['empresa', 'grupo', 'subgrupo', 'tipo_gasto', 'anio', 'mes', 'monto']
        widgets = {
            'anio': forms.NumberInput(attrs={'min':2024}),
            'mes': forms.Select(choices=[('', '---')] + [(i, i) for i in range(1,13)]),
            'monto': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Recibes el usuario desde la vista
        super().__init__(*args, **kwargs)
        
        # Si el usuario no es superusuario, limita la empresa
        if user and not user.is_superuser:
            if hasattr(user, 'perfilusuario'):
                self.fields['empresa'].queryset = Empresa.objects.filter(pk=user.perfilusuario.empresa.id)
                self.fields['empresa'].initial = user.perfilusuario.empresa
                self.fields['empresa'].widget.attrs['readonly'] = True
                self.fields['empresa'].widget.attrs['disabled'] = True
            
            # Elimina el campo del form si no es superusuario
                self.fields.pop('empresa')



class PresupuestoCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label="Archivo Excel")