from django import forms
from jmespath import Options
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
            "proindiviso",
        ]
        widgets = {
            "numero": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Número, Codigo o Id."}
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
            "proindiviso": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "% Proindiviso",
                    "step": "0.0001",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Observaciones",
                }
            ),
        }
        labels = {
            "numero": "Número, Codigo o Id.",
            "ubicacion": "Ubicación",
            "status": "Estatus",
            "cliente": "Arrendatario/Inquilino/Cliente",
            "proindiviso": "% Indiviso",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        empresa_usuario = None

        if user and not user.is_superuser:
            self.fields["empresa"].widget = forms.HiddenInput()
            empresa_usuario = user.perfilusuario.empresa
            self.fields["cliente"].queryset = Cliente.objects.filter(
                empresa=empresa_usuario
            )
        else:
            self.fields["cliente"].queryset = Cliente.objects.all()

        # --- NUEVO: ajustes según segmento de la empresa ---
        if empresa_usuario and empresa_usuario.segmento == "habitacional":
            self.fields["cliente"].label = "Propietario / Residente"
            self.fields["numero"].widget.attrs["placeholder"] = (
                "Número de casa / departamento"
            )

            # "Giro" no aplica a una vivienda -- se oculta y deja de ser relevante
            self.fields["giro"].required = False
            self.fields["giro"].widget = forms.HiddenInput()

            self.fields["ubicacion"].required = False
            self.fields["ubicacion"].widget = forms.HiddenInput()

            # Solo mostrar tipos de propiedad habitacionales
            self.fields["tipo_propiedad"].choices = [
                c
                for c in LocalComercial.TIPO_CHOICES
                if c[0] in ("casa", "departamento")
            ]
        else:
            # Segmento comercial (o superusuario sin empresa fija todavía):
            # solo mostrar tipos de propiedad comerciales
            self.fields["tipo_propiedad"].choices = [
                c
                for c in LocalComercial.TIPO_CHOICES
                if c[0] in ("local", "oficina", "bodega", "terreno")
            ]

    def clean(self):
        cleaned_data = super().clean()
        numero = cleaned_data.get("numero")
        empresa = cleaned_data.get("empresa")

        if numero and empresa:
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
