from django import forms
from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "empresa",
            "nombre",
            "rfc",
            "telefono",
            "email",
            "direccion",
            "activo",
        ]

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