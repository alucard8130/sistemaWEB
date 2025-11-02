from django import forms
from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "empresa",
            "nombre",
            "rfc",
            "repse_numero",
            "repse_vigencia",
            "telefono",
            "email",
            "direccion",
            "activo",
        ]
        widgets = {
            "repse_vigencia": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user and not self.user.is_superuser:
            self.fields['empresa'].widget = forms.HiddenInput()
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(
                widget,
                (forms.TextInput, forms.Select, forms.EmailInput, forms.Textarea),
            ):
                widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        # Forzar empresa para usuarios normales
        if self.user and not self.user.is_superuser:
            cleaned_data['empresa'] = self.user.perfilusuario.empresa
            self.fields['empresa'].initial = self.user.perfilusuario.empresa
        return cleaned_data

    def clean_rfc(self):
        rfc = self.cleaned_data.get('rfc')
        empresa = self.cleaned_data.get('empresa')
        if rfc and empresa:
            qs = Proveedor.objects.filter(rfc=rfc, empresa=empresa)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ya existe un/a Proveedor con este/a RFC para esta empresa.")
        return rfc

    def clean_repse_vigencia(self):
        fecha = self.cleaned_data.get('repse_vigencia')
        # Si el campo viene vacío o como cadena vacía, conserva la original
        if not fecha or str(fecha).strip() == "":
            return self.instance.repse_vigencia
        return fecha
    
class ProveedorCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label="Archivo Excel", help_text="Sube un archivo .xlsx con los datos de los proveedores.")