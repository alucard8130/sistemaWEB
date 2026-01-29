from django import forms
from clientes.models import Cliente
from .models import LocalComercial
from empresas.models import Empresa


class LocalComercialForm(forms.ModelForm):
    class Meta:
        model = LocalComercial
        fields = [
            "numero",
            "propietario",
            "cliente",
            "empresa",
            "tipo_propiedad",
            "superficie_m2",
            "cuota",
            "giro",
            "ubicacion",
            "status",
            "observaciones",
            "es_cuota_anual",
        ]
        widgets = {
            "numero": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Número"}
            ),
            "propietario": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Propietario"}
            ),
            "cliente": forms.Select(attrs={"class": "form-control"}),
            "empresa": forms.Select(attrs={"class": "form-control"}),
            "tipo_propiedad": forms.Select(attrs={"class": "form-control"}),
            "superficie_m2": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Superficie_m2"}
            ),
            "cuota": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Importe Cuota Mensual"}
            ),
            "es_cuota_anual": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-top: 0.3rem;"}
            ),
            "giro": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Giro"}
            ),
            "ubicacion": forms.Textarea(
                attrs={"rows": 2, "class": "form-control", "placeholder": "Ubicación"}
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Observaciones",
                }
            ),
        }
        labels = {
            "numero": "Número",
            "ubicacion": "Ubicación",
            "status": "Estatus",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # obtenemos el usuario desde la vista
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            self.fields["empresa"].widget = forms.HiddenInput()
            empresa = user.perfilusuario.empresa
            self.fields["cliente"].queryset = Cliente.objects.filter(empresa=empresa)
        else:
            self.fields["cliente"].queryset = Cliente.objects.all()
        # Deshabilita el campo cliente si se está editando un local existente
        if self.instance and self.instance.pk:
            self.fields["cliente"].disabled = True
            self.fields["numero"].disabled = True
            # self.fields['status'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        numero = cleaned_data.get("numero")
        empresa = cleaned_data.get("empresa")

        if numero and empresa:
            # Buscar duplicado activo
            duplicado = LocalComercial.objects.filter(
                numero=numero, empresa=empresa
            ).exclude(pk=self.instance.pk)
            if duplicado.exists():
                raise forms.ValidationError(
                    f"Ya existe un local con número '{numero}' en esta empresa."
                )
        return cleaned_data


class LocalCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label="Archivo Excel (.xlsx)")
