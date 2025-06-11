# presupuestos/forms.py
from django import forms
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
