from decimal import Decimal
from django import forms
from .models import FondeoCajaChica, GastoCajaChica, ValeCaja



class FondeoCajaChicaForm(forms.ModelForm):
    class Meta:
        model = FondeoCajaChica
        fields = [
            "numero_cheque",
            "importe_cheque",
            "empleado_asignado",
            "fecha",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "empleado_asignado": forms.Select(attrs={"class": "form-control"}),
            "numero_cheque": forms.TextInput(attrs={"class": "form-control"}),
            "importe_cheque": forms.NumberInput(attrs={"class": "form-control"}),
        }

    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )


class GastoCajaChicaForm(forms.ModelForm):
    class Meta:
        model = GastoCajaChica
        fields = [
            "fondeo",
            "proveedor",
            "tipo_gasto",
            "descripcion",
            "importe",
            "fecha",
        ]
        widgets = {
            "fondeo": forms.Select(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "proveedor": forms.Select(attrs={"class": "form-control","required": True}),
            "tipo_gasto": forms.Select(attrs={"class": "form-control","required": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control"}),
            "importe": forms.NumberInput(attrs={"class": "form-control"}),
        }

    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    

class ValeCajaForm(forms.ModelForm):
    class Meta:
        model = ValeCaja
        fields = [
            "fondeo",
            "tipo_gasto",
            "descripcion",
            "importe",
            "status",
            "fecha",
            "recibido_por",
            "autorizado_por",
            
        ]
        widgets = {
            "fondeo": forms.Select(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "recibido_por": forms.Select(attrs={"class": "form-control","required": True}),
            "autorizado_por": forms.TextInput(attrs={"class": "form-control","required": True}),
            "tipo_gasto": forms.Select(attrs={"class": "form-control","required": True}),
            "descripcion": forms.Textarea(attrs={"class": "form-control"}),
            "importe": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )


class ComprobarValeForm(forms.Form):
    importe_comprobado = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.00'),
        label="Importe a comprobar",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"})
    )
    descripcion = forms.CharField(
        required=True,
        label="Descripción / Observaciones",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3})
    )