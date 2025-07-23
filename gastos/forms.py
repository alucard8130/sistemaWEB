from django import forms

from empleados.models import Empleado
from proveedores.models import Proveedor
from .models import Gasto, GrupoGasto, SubgrupoGasto, TipoGasto
from django import forms
from .models import PagoGasto


class SubgrupoGastoForm(forms.ModelForm):
    class Meta:
        model = SubgrupoGasto
        fields = ['grupo', 'nombre']

        widgets = {
            'grupo': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }
      
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Todos los grupos son universales
        self.fields['grupo'].queryset = GrupoGasto.objects.all()

class TipoGastoForm(forms.ModelForm):
    class Meta:
        model = TipoGasto
        fields = ['empresa', 'subgrupo', 'nombre', 'descripcion']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Subgrupos universales
        self.fields['subgrupo'].queryset = SubgrupoGasto.objects.all()
        # Empresa solo para el usuario correspondiente
        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].initial = user.perfilusuario.empresa

        #  Agregar clases Bootstrap
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                # Detectar si el widget es tipo Select
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'

                # Asignar placeholders específicos
                if field_name == 'empresa':
                    field.widget.attrs['placeholder'] = 'Selecciona una empresa'
                elif field_name == 'subgrupo':
                    field.widget.attrs['placeholder'] = 'Selecciona un subgrupo'
                elif field_name == 'nombre':
                    field.widget.attrs['placeholder'] = 'Nombre'
                elif field_name == 'descripcion':
                    field.widget.attrs['placeholder'] = 'Descripción'
        # labels con tilde
        self.fields['descripcion'].label = 'Descripción'

                    
#solicitud de gastos
class GastoForm(forms.ModelForm):
    origen_tipo = forms.ChoiceField(choices=[('proveedor', 'Proveedor'), ('empleado', 'Empleado')],label="Tipo de origen", required=True,
                widget=forms.Select(attrs={
                    'class': 'form-select'
                }))


 
    class Meta:
        model = Gasto
        fields = ['empresa','origen_tipo', 'proveedor', 'empleado', 'tipo_gasto', 'descripcion', 'fecha', 'monto' ,'retencion_iva', 'retencion_isr','comprobante', 'observaciones']
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'empresa': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tipo_gasto': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'retencion_iva': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'retencion_isr': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'comprobante': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'descripcion': forms.Textarea(attrs={
                'rows':2,
                'class': 'form-control'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows':2,
                'class': 'form-control'
            }),
        }

      

    def __init__(self, *args, **kwargs):
        modo = kwargs.pop('modo', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Solo superusuario puede elegir empresa, los demás sólo la propia
        if not user or not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()

        #self.fields['empresa'].required = False
        self.fields['descripcion'].required = True
        self.fields['comprobante'].required = True

        # Por defecto vacíos si no hay empresa
        self.fields['proveedor'].queryset = Proveedor.objects.none()
        self.fields['empleado'].queryset = Empleado.objects.none()

        #if not user or not user.is_superuser:
        #    self.fields['proveedor'].disabled = True
         #   self.fields['origen_tipo'].disabled = True
          #  self.fields['empleado'].disabled = True
          
        if modo == 'editar':
            self.fields['origen_tipo'].disabled = True
            self.fields['proveedor'].disabled = True

        if user:
            if user.is_superuser:
                # Para superusuario, se muestran todos
                self.fields['proveedor'].queryset = Proveedor.objects.all()
                self.fields['empleado'].queryset = Empleado.objects.all()
            else:
                empresa = getattr(user.perfilusuario, 'empresa', None)
                if empresa:
                    self.fields['proveedor'].queryset = Proveedor.objects.filter(empresa=empresa)
                    self.fields['empleado'].queryset = Empleado.objects.filter(empresa=empresa)
                    self.fields['tipo_gasto'].queryset = TipoGasto.objects.filter(empresa=empresa)
        
    #si se selecciona proveedor, empleado no es requerido y viceversa
    def clean(self):
        cleaned_data = super().clean()
        proveedor = cleaned_data.get('proveedor')
        empleado = cleaned_data.get('empleado')
        origen_tipo = cleaned_data.get('origen_tipo')

        if origen_tipo == 'proveedor' and not proveedor:
            self.add_error('proveedor', 'Debes seleccionar un proveedor.')
        if origen_tipo == 'empleado' and not empleado:
            self.add_error('empleado', 'Debes seleccionar un empleado.')
        # Opcional: si quieres que uno de los dos sea obligatorio siempre
        if not proveedor and not empleado:
            raise forms.ValidationError('Debes seleccionar un proveedor o un empleado.')
        return cleaned_data



class PagoGastoForm(forms.ModelForm):
    class Meta:
        model = PagoGasto
        fields = ['fecha_pago', 'monto', 'forma_pago','comprobante', 'referencia']
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
            'referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Referencia'
            }),
        }
   
class GastosCargaMasivaForm(forms.Form):
        archivo = forms.FileField(label='Archivo Excel (.xlsx)')     