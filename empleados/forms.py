from django import forms
from .models import Empleado, Incidencia

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['empresa', 'nombre','rfc', 'puesto', 'departamento','telefono', 'email', 'activo','hora_entrada_esperada', 'hora_salida_esperada', 'tolerancia_minutos',]

        widgets = {
                'hora_entrada_esperada': forms.TimeInput(attrs={'type': 'time'}),
                'hora_salida_esperada': forms.TimeInput(attrs={'type': 'time'}),
            }
        labels = {
                'hora_entrada_esperada': 'Hora de entrada esperada',
                'hora_salida_esperada': 'Hora de salida esperada',
                'tolerancia_minutos': 'Tolerancia de retardo (minutos)',
            }
        help_texts = {
                'hora_entrada_esperada': 'Se usa para el checador de asistencia: si el empleado marca su entrada después de esta hora + la tolerancia, se registra un retardo automáticamente.',
                'tolerancia_minutos': 'Minutos de gracia antes de contar retardo (ej. 10 = hasta 10 min tarde no cuenta).',
            }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        if user and not user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()

        self.fields['empresa'].required = False

        # Los campos de horario son opcionales -- un empleado puede no
        # tener horario fijo (ej. turnos variables) y el checador sigue
        # funcionando igual, solo sin detectar retardo automático.
        self.fields['hora_entrada_esperada'].required = False
        self.fields['hora_salida_esperada'].required = False

        # Aplicar Bootstrap a cada campo
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, (forms.TextInput, forms.Select, forms.EmailInput, forms.Textarea,forms.NumberInput)):
                widget.attrs['class'] = 'form-control'

class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['empleado', 'tipo', 'fecha', 'fecha_fin', 'dias', 'descripcion', 'numero_incapacidad_imss', 'importe']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'importe': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
        self.fields['numero_incapacidad_imss'].required = False  # Por defecto no requerido
        self.fields['importe'].required = False  # Por defecto no requerido

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        numero_incapacidad = cleaned_data.get('numero_incapacidad_imss')
        if tipo == 'incapacidad' and not numero_incapacidad:
            self.add_error('numero_incapacidad_imss', 'Este campo es obligatorio para incidencias de incapacidad.')
        return cleaned_data
    

