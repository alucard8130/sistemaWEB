from django import forms
from .models import CobroOtrosIngresos, Factura, FacturaOtrosIngresos, Pago
from django.db import models
from empresas.models import Empresa

class FacturaForm(forms.ModelForm):
    TIPO_ORIGEN_CHOICES = [
        ('local', 'Local Comercial'),
        ('area_comun', 'Área Común'),
    ]
    tipo_origen = forms.ChoiceField(choices=TIPO_ORIGEN_CHOICES, label="Origen de la factura", required=True, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Factura
        #fields = ['cliente', 'local', 'area_comun','tipo_cuota', 'fecha_vencimiento', 'monto', 'estatus','observaciones']
        fields = ['cliente', 'local', 'area_comun','tipo_cuota', 'fecha_vencimiento', 'monto','cfdi', 'observaciones']
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select'
                }),
            'local': forms.Select(attrs={
                'class': 'form-select'
                }),
            'area_comun': forms.Select(attrs={
                'class': 'form-select'
            }),
             'tipo_cuota': forms.Select(attrs={
                'class': 'form-select'                
                }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
                }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',                                                                                                                                                                
                'placeholder': 'Monto'
                }),
            'cfdi': forms.FileInput(attrs={
                'class': 'form-control'
                }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Observaciones'
                }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # campos no requeridos
        self.fields['local'].required = False
        self.fields['area_comun'].required = False

        if self.user and not self.user.is_superuser:
            empresa = self.user.perfilusuario.empresa
            self.fields['cliente'].queryset = self.fields['cliente'].queryset.filter(empresa=empresa)
            self.fields['local'].queryset = self.fields['local'].queryset.filter(empresa=empresa)
            self.fields['area_comun'].queryset = self.fields['area_comun'].queryset.filter(empresa=empresa)

    def clean(self):
        cleaned_data = super().clean()
        monto = cleaned_data.get('monto')
        local= cleaned_data.get('local')
        area_comun = cleaned_data.get('area_comun')
        
        if not local and not area_comun:
            self.add_error(None, 'Debe seleccionar al menos un Local o Área Común.')

        if monto is None or monto <= 0:
            self.add_error('monto', 'El monto debe ser un valor positivo.')
        return cleaned_data

    def clean_fecha_vencimiento(self):
        fecha_vencimiento = self.cleaned_data.get('fecha_vencimiento')
        if not fecha_vencimiento:
            raise forms.ValidationError("La fecha de vencimiento es obligatoria.")
        return fecha_vencimiento        
      
class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['fecha_pago', 'monto', 'forma_pago','comprobante', 'observaciones']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Monto'
            }),
            'forma_pago': forms.Select(attrs={
                'class': 'form-select'
            }),
            'comprobante': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Observaciones'
            }),
                
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Monto no requerido desde el principio (el clean lo maneja)
        self.fields['monto'].required = False

    def clean(self):
        cleaned_data = super().clean()
        forma_pago = cleaned_data.get('forma_pago')
        monto = cleaned_data.get('monto')
    
        if forma_pago != 'nota_credito' and (monto is None or monto == 0):
            self.add_error('monto', 'El monto es obligatorio excepto para Nota de Crédito.')
        
        if forma_pago == 'nota_credito':
            cleaned_data['monto'] = 0  # Si es nota de crédito, pone monto a cero
        return cleaned_data
        
    def clean_fecha_pago(self):
        fecha_pago = self.cleaned_data['fecha_pago']
        if fecha_pago == None:
            raise forms.ValidationError("La fecha de pago es obligatoria.")
        return fecha_pago


class FacturaCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label='Archivo Excel (.xlsx)')

class FacturaEditForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['cliente', 'local', 'area_comun', 'folio', 'fecha_vencimiento', 'monto','tipo_cuota','cfdi', 'estatus', 'observaciones']    
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select'
            }),
            'local': forms.Select(attrs={
                'class': 'form-select'
            }),
            'area_comun': forms.Select(attrs={
                'class': 'form-select'
            }),
            'folio': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'tipo_cuota': forms.Select(attrs={
                'class': 'form-select'
            }),
            'cfdi': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'estatus': forms.Select(attrs={
                'class': 'form-select'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deshabilita el campo cliente para evitar edición
        self.fields['cliente'].disabled = True
        self.fields['estatus'].disabled = True
        self.fields['area_comun'].disabled = True
        self.fields['local'].disabled = True
        
        
            
class FacturaOtrosIngresosForm(forms.ModelForm):
    class Meta:
        model = FacturaOtrosIngresos
        fields = ['cliente', 'tipo_ingreso', 'fecha_vencimiento', 'monto', 'cfdi','observaciones']
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select'             
            }),
            'tipo_ingreso': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'cfdi': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control'
            }),
        }            
   
class CobroForm(forms.ModelForm):
    class Meta:
        model = CobroOtrosIngresos
        fields = ['fecha_cobro', 'monto', 'forma_cobro', 'comprobante', 'observaciones']
        widgets = {
            'fecha_cobro': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Monto'
            }),
            'forma_cobro': forms.Select(attrs={
                'class': 'form-select'
            }),
            'comprobante': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Observaciones'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Monto no requerido desde el principio (el clean lo maneja)
        self.fields['monto'].required = False


