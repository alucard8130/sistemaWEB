from django import forms

from clientes.models import Cliente
from .models import CobroOtrosIngresos, Factura, FacturaOtrosIngresos, Pago, TipoOtroIngreso
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
        fields = ['cliente', 'local', 'area_comun','tipo_cuota', 'fecha_vencimiento', 'monto','observaciones']
        labels = {'observaciones': 'Comentario'}
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
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Comentario'
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
            raise forms.ValidationError("La fecha de la factura es obligatoria.")
        return fecha_vencimiento        
      
class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['fecha_pago', 'monto', 'forma_pago', 'observaciones']
        labels = {'observaciones': 'Comentario'}
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
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Comentario'
            }),
                
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        fields = ['cliente', 'local', 'area_comun', 'folio', 'fecha_vencimiento', 'monto','tipo_cuota', 'estatus', 'observaciones']
        labels = {'observaciones': 'Comentario'}   
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
            }, format='%Y-%m-%d'),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'tipo_cuota': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estatus': forms.Select(attrs={
                'class': 'form-select'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'comentario'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estatus'].disabled = True
        self.fields['area_comun'].disabled = True
        self.fields['local'].disabled = True

    def clean_fecha_vencimiento(self):
        fecha = self.cleaned_data.get('fecha_vencimiento')
        print("Valor recibido en fecha_vencimiento:", fecha)
        # Si el campo viene vacío o como cadena vacía, conserva la original
        if not fecha or str(fecha).strip() == "":
            return self.instance.fecha_vencimiento
        return fecha


class FacturaOtrosIngresosForm(forms.ModelForm):
    class Meta:
        model = FacturaOtrosIngresos
        fields = ['cliente', 'tipo_ingreso', 'fecha_vencimiento', 'monto', 'observaciones']
        labels = {'observaciones': 'Comentario'}
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
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Comentario'
            }),
        }  

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'perfilusuario'):
            empresa = user.perfilusuario.empresa
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
            self.fields['tipo_ingreso'].queryset = TipoOtroIngreso.objects.filter(empresa=empresa)
        else:
            self.fields['tipo_ingreso'].queryset = TipoOtroIngreso.objects.all()    
   
class CobroForm(forms.ModelForm):
    class Meta:
        model = CobroOtrosIngresos
        fields = ['fecha_cobro', 'monto', 'forma_cobro', 'observaciones']
        labels = {'observaciones': 'Comentario'}
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
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Comentario'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Monto no requerido desde el principio (el clean lo maneja)
        self.fields['monto'].required = False


    def clean(self):
        cleaned_data = super().clean()
        forma_cobro = cleaned_data.get('forma_cobro')
        monto = cleaned_data.get('monto')

        if forma_cobro != 'nota_credito' and (monto is None or monto == 0):
            self.add_error('monto', 'El monto es obligatorio excepto para Nota de Crédito.')

        if forma_cobro == 'nota_credito':
            cleaned_data['monto'] = 0  # Si es nota de crédito, pone monto a cero
        return cleaned_data    

class TipoOtroIngresoForm(forms.ModelForm):
    class Meta:
        model = TipoOtroIngreso
        fields = ['nombre']




# Formulario para timbrar factura
class TimbrarFacturaForm(forms.Form):
    TAX_OBJECT_CHOICES = [
        ("02", "Sí objeto de impuesto"),
        ("01", "No objeto de impuesto"),
    ]
    PAYMENT_METHOD_CHOICES = [
        ("PUE", "Pago en una sola exhibición"),
        ("PPD", "Pago en parcialidades o diferido"),
    ]
    PAYMENT_FORM_CHOICES = [
        ("01", "Efectivo"),
        ("02", "Cheque nominativo"),
        ("03", "Transferencia electrónica de fondos"),
        ("04", "Tarjeta de crédito"),
        ("28", "Tarjeta de débito"),
        ("99", "Por definir"),
        # Agrega más según catálogo SAT si lo necesitas
    ]
    tax_object = forms.ChoiceField(choices=TAX_OBJECT_CHOICES, label="Objeto de impuesto")
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES, label="Método de pago")
    payment_form = forms.ChoiceField(choices=PAYMENT_FORM_CHOICES, label="Forma de pago")