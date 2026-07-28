from django import forms
from .models import CuentaBancaria, Empresa


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            "nombre",
            "rfc",
            "regimen_fiscal",
            "codigo_postal",
            "direccion",
            "telefono",
            "email",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre de la empresa"}
            ),
            "rfc": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "RFC"}
            ),
            "regimen_fiscal": forms.Select(
                attrs={"class": "form-control", "placeholder": "Régimen Fiscal"}
            ),
            "direccion": forms.Textarea(
                attrs={"rows": 2, "class": "form-control", "placeholder": "Dirección"}
            ),
            "codigo_postal": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Código Postal"}
            ),
            "telefono": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Teléfono"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email"}
            ),
        }
        labels = {
            "nombre": "Nombre de la empresa",
            "rfc": "RFC",
            "regimen_fiscal": "Régimen Fiscal",
            "codigo_postal": "Código Postal",
            "direccion": "Dirección",
            "telefono": "Teléfono",
            "email": "Email",
        }


class CuentaBancariaForm(forms.ModelForm):
    class Meta:
        model = CuentaBancaria
        fields = [
            "banco",
            "numero_cuenta",
            "clabe",
            "moneda",
            "tipo_cuenta",
            "saldo_inicial",
            "cuenta_contable",  # NUEVO
        ]
        widgets = {
            "banco": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "numero_cuenta": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Número de Cuenta"}
            ),
            "clabe": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "CLABE interbancaria",
                }
            ),
            "moneda": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "tipo_cuenta": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "saldo_inicial": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "cuenta_contable": forms.Select(  # NUEVO
                attrs={
                    "class": "form-control",
                }
            ),
        }
        labels = {
            "banco": "Banco",
            "numero_cuenta": "Número de Cuenta",
            "clabe": "CLABE interbancaria",
            "moneda": "Moneda",
            "tipo_cuenta": "Tipo de Cuenta",
            "saldo_inicial": "Saldo inicial",
            "cuenta_contable": "Cuenta contable",  # NUEVO
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        # Filtra el catálogo de cuentas contables a las de esta empresa,
        # y lo hace opcional (no todas las cuentas necesitan homologarse de inmediato).
        self.fields['cuenta_contable'].required = False
        if empresa:
            from gastos.models import CuentaContable  # ajusta el import
            self.fields['cuenta_contable'].queryset = CuentaContable.objects.filter(empresa=empresa, activa=True)
        else:
            from gastos.models import CuentaContable
            self.fields['cuenta_contable'].queryset = CuentaContable.objects.none()

    def clean_saldo_inicial(self):
        saldo = self.cleaned_data.get("saldo_inicial")
        if saldo is None:
            return 0
        if saldo < 0:
            raise forms.ValidationError("El saldo inicial no puede ser negativo.")
        return saldo

    def clean_clabe(self):
        clabe = self.cleaned_data.get("clabe")
        if clabe and len(clabe) != 18:
            raise forms.ValidationError("La CLABE debe tener exactamente 18 dígitos.")
        if clabe and not clabe.isdigit():
            raise forms.ValidationError("La CLABE debe contener solo dígitos.")
        return clabe

    def clean_numero_cuenta(self):
        numero_cuenta = self.cleaned_data.get("numero_cuenta")
        numero_cuenta_actual = self.instance.numero_cuenta if self.instance.pk else None
        if numero_cuenta and numero_cuenta != numero_cuenta_actual:
            if CuentaBancaria.objects.filter(numero_cuenta=numero_cuenta).exists():
                raise forms.ValidationError(
                    "El número de cuenta ya existe. Por favor, elige otro."
                )
        if numero_cuenta and not numero_cuenta.isdigit():
            raise forms.ValidationError(
                "El número de cuenta debe contener solo dígitos."
            )
        return numero_cuenta
