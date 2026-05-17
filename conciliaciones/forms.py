
from django import forms
from .models import EstadoCuentaBancario, CuentaBancaria

class EstadoCuentaBancarioForm(forms.ModelForm):
    fecha_inicio = forms.DateField(label="Fecha inicio del periodo", widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_fin = forms.DateField(label="Fecha fin del periodo", widget=forms.DateInput(attrs={'type': 'date'}))
                                
    class Meta:
        model = EstadoCuentaBancario
        fields = [ 'cuenta_bancaria', 'archivo', 'fecha_inicio', 'fecha_fin']


    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.filter(empresa=empresa)
        else:
            self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.none()

        # if 'empresa' in self.data:
        #     try:
        #         empresa_id = int(self.data.get('empresa'))
        #         self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.filter(empresa_id=empresa_id)
        #     except (ValueError, TypeError):
        #         pass
        # elif empresa:
        #     self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.filter(empresa=empresa)
        # elif self.instance.pk:
        #     self.fields['cuenta_bancaria'].queryset = self.instance.empresa.cuentabancaria_set.all()

class ConciliacionBancariaForm(forms.Form):
    estado_cuenta = forms.ModelChoiceField(queryset=EstadoCuentaBancario.objects.all(), label="Estado de cuenta a conciliar")
    # Puedes agregar más campos si necesitas parámetros de conciliación (tolerancia, etc.)