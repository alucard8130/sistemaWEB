from decimal import Decimal

from django import forms

from clientes.models import Cliente
from empresas.models import CuentaBancaria

from .models import AreaComun

#from empresas.models import Empresa


class AreaComunForm(forms.ModelForm):
    class Meta:
        model = AreaComun
        fields = [  # noqa: RUF012
            "numero",
            "cliente",
            "empresa",
            "superficie_m2",
            "tipo_area",
            "cantidad_areas",
            "cuota",
            "deposito",
            "giro",
            "ubicacion",
            "fecha_inicial",
            "fecha_fin",
            "status",
            "observaciones",
            "es_cuota_anual",
            "es_cuota_variable",
        ]
        widgets = {  # noqa: RUF012
            "numero": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Número, Codigo o Id."}
            ),
            "cliente": forms.Select(attrs={"class": "form-control"}),
            "empresa": forms.Select(attrs={"class": "form-control"}),
            "superficie_m2": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Superficie_m2"}
            ),
            "tipo_area": forms.Select(attrs={"class": "form-control"}),
            "cantidad_areas": forms.TextInput(attrs={"class": "form-control"}),
            "cuota": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Importe Cuota Mensual"}
            ),
            "es_cuota_anual": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-top: 0.3rem;"}
            ),
            "es_cuota_variable": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "margin-top: 0.3rem;"}
            ),
            "deposito": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Importe Depósito Garantía"}
            ),
            "giro": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Giro"}
            ),
            "ubicacion": forms.Textarea(
                attrs={"rows": 2, "class": "form-control", "placeholder": "Ubicación"}
            ),
            "fecha_inicial": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
            ),
            "fecha_fin": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
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
        labels = {  # noqa: RUF012
            "numero": "Número, Codigo o Id.",
            "tipo_area": "Tipo de área",
            "cantidad_areas": "Cantidad de áreas",
            "deposito": "Depósito en garantía",
            "ubicacion": "Ubicación",
            "status": "Estatus",
            "cliente": "Cliente",
            "es_cuota_anual": "Es cuota anual",
            "es_cuota_variable": "Es cuota variable",
        }

    def __init__(self, *args, **kwargs):
        # self.user = kwargs.pop('user', None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            self.fields["empresa"].widget = forms.HiddenInput()
            empresa = user.perfilusuario.empresa
            self.fields["empresa"].initial = empresa  # <-- Asigna el valor aquí
            self.fields["cliente"].queryset = Cliente.objects.filter(empresa=empresa)
        else:
            self.fields["cliente"].queryset = Cliente.objects.all()

    
        if self.instance and self.instance.pk:
            self.fields["numero"].disabled = True
            # NUEVO -- cliente y status ya NO se deshabilitan: se necesitan
            # editables para que las reglas automáticas de clean() (más abajo)
            # puedan aplicar -- mismo criterio que LocalComercialForm.

        # NUEVO -- estos campos dependen del status resultante (ver clean()),
        # así que se aflojan aquí y clean() decide si son obligatorios o no.
        self.fields["cuota"].required = False
        self.fields["giro"].required = False
        self.fields["fecha_inicial"].required = False
        self.fields["fecha_fin"].required = False


    def clean_cuota(self):
        cuota = self.cleaned_data.get("cuota")
        es_variable = self.data.get("es_cuota_variable") or self.initial.get("es_cuota_variable")
        if es_variable:
            return cuota or Decimal("0")
        if cuota is None or cuota <= 0:
            raise forms.ValidationError(
                "La cuota debe ser mayor a $0.00 -- no se puede dejar en cero. "
                "Si el importe de esta área varía cada vez, marca \"¿Cuota variable?\"."
            )
        return cuota
 
    def clean(self):
        cleaned_data = super().clean()
        numero = cleaned_data.get("numero")
        empresa = cleaned_data.get("empresa")
        status = cleaned_data.get("status")
        cliente = cleaned_data.get("cliente")

        if numero and empresa:
            qs = AreaComun.objects.filter(
                numero__iexact=numero, empresa=empresa, activo=True
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "Ya existe un área común con ese número en esta empresa."
                )

        # ---- Reglas automáticas de cliente/status (mismo criterio que Locales) ----
        cliente_original_id = self.instance.cliente_id if self.instance.pk else None
        cliente_nuevo_id = cliente.id if cliente else None
        se_asigno_cliente_nuevo = (
            cliente_nuevo_id is not None and cliente_nuevo_id != cliente_original_id
        )

        if se_asigno_cliente_nuevo:
            # Se asignó un cliente nuevo/distinto -- el área pasa a "Ocupado"
            # automáticamente, sin importar qué status se haya seleccionado.
            cleaned_data["status"] = "ocupado"
            status = "ocupado"
        elif status == "disponible":
            # NUEVO -- al quedar Disponible, se limpia TODO lo relacionado
            # al contrato anterior: cliente, giro, fecha_inicial, fecha_fin.
            # La cuota NO se toca (se queda capturada para la próxima renta).
            cleaned_data["cliente"] = None
            cleaned_data["giro"] = None
            cleaned_data["fecha_inicial"] = None
            cleaned_data["fecha_fin"] = None

        # ---- Campos obligatorios SOLO si el área queda "Ocupado" ----
        if status == "ocupado":
            if not cleaned_data.get("fecha_inicial"):
                raise forms.ValidationError(
                    "Debe ingresar la fecha inicial del contrato -- el área quedará Ocupada."
                )
            if not cleaned_data.get("fecha_fin"):
                raise forms.ValidationError(
                    "Debe ingresar la fecha fin del contrato -- el área quedará Ocupada."
                )
            if not cleaned_data.get("giro"):
                raise forms.ValidationError(
                    "Debe ingresar el giro del cliente -- el área quedará Ocupada."
                )

        fecha_inicial = cleaned_data.get("fecha_inicial")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_inicial and fecha_fin and fecha_inicial > fecha_fin:
            raise forms.ValidationError(
                "La fecha inicial no puede ser posterior a la fecha fin."
            )

        return cleaned_data



class AsignarClienteForm(forms.ModelForm):
    class Meta:
        model = AreaComun
        fields = ["cliente", "giro", "fecha_inicial", "fecha_fin"]  # noqa: RUF012
        widgets = {  # noqa: RUF012
            "fecha_inicial": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop("empresa", None)
        super().__init__(*args, **kwargs)
        # NUEVO -- filtra por empresa, igual que AreaComunForm
        if empresa:
            self.fields["cliente"].queryset = Cliente.objects.filter(empresa=empresa)
        else:
            self.fields["cliente"].queryset = Cliente.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get("cliente")
        giro = cleaned_data.get("giro")
        fecha_inicial = cleaned_data.get("fecha_inicial")
        fecha_fin = cleaned_data.get("fecha_fin")

        if not cliente:
            self.add_error("cliente", "Debe seleccionar un cliente.")
        if not giro:
            self.add_error("giro", "Debe ingresar el giro del cliente.")
        if not fecha_inicial:
            self.add_error("fecha_inicial", "Debe ingresar la fecha inicial.")
        if not fecha_fin:
            self.add_error("fecha_fin", "Debe ingresar la fecha fin.")
        if fecha_inicial and fecha_fin and fecha_inicial > fecha_fin:
            self.add_error("fecha_fin", "La fecha fin no puede ser anterior a la fecha inicial.")

        return cleaned_data


class AreaComunCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label="Archivo Excel (.xlsx)")


#from django import forms


class DatosContratoForm(forms.Form):
    def __init__(self, *args, **kwargs):
        tipo_contribuyente = kwargs.pop("tipo_contribuyente", None)
        empresa = kwargs.pop("empresa", None)  # ← nuevo parámetro
        super().__init__(*args, **kwargs)

        # Selección de cuenta bancaria de la empresa
        if empresa:
            cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)
            self.fields["cuenta_bancaria_id"] = forms.ModelChoiceField(
                queryset=cuentas,
                label="Cuenta bancaria para el contrato",
                empty_label="Selecciona una cuenta bancaria",
                widget=forms.Select(attrs={"class": "form-select"}),
                help_text="Esta cuenta aparecerá en la cláusula de pago del contrato.",
            )
            
        # Campos de datos arrendador (siempre)
        self.fields["escritura_numero_arrendador"] = forms.CharField(
            label="Número Escritura Arrendador", max_length=50
        )
        self.fields["escritura_fecha_arrendador"] = forms.DateField(
            label="Fecha Escritura Arrendador", widget=forms.DateInput(attrs={"type": "date"})
        )
        self.fields["notario_nombre_arrendador"] = forms.CharField(
            label="Nombre Notario Arrendador", max_length=100
        )
        self.fields["notario_numero_arrendador"] = forms.CharField(
            label="Número Notario Arrendador", max_length=50
        )
        self.fields["notario_ciudad_arrendador"] = forms.CharField(
            label="Ciudad Notario Arrendador", max_length=100
        )
        # self.fields["clabe_interbancaria_arrendador"] = forms.CharField(
        #     label="CLABE Interbancaria Arrendador", max_length=50
        # )
        self.fields["apoderado_nombre_arrendador"] = forms.CharField(
            label="Nombre Apoderado Arrendador", max_length=100
        )
        self.fields["apoderado_numero_escritura_arrendador"] = forms.CharField(
            label="Número Escritura Apoderado", max_length=50
        )
        self.fields["apoderado_escritura_fecha_arrendador"] = forms.DateField(
            label="Fecha Escritura del Apoderado", widget=forms.DateInput(attrs={"type": "date"})
        )
        self.fields["apoderado_notario_nombre_arrendador"] = forms.CharField(
            label="Nombre Notario del Apoderado", max_length=100
        )
        self.fields["apoderado_notario_numero_arrendador"] = forms.CharField(
            label="Número Notario del Apoderado", max_length=50
        )
        self.fields["apoderado_notario_ciudad_arrendador"] = forms.CharField(
            label="Ciudad Notario del Apoderado", max_length=100
        )
        self.fields["fecha_firma_contrato_arrendador"] = forms.DateField(
            label="Fecha de Firma del Contrato", widget=forms.DateInput(attrs={"type": "date"})
        )

        # Si es persona moral, agrega los campos extra
        if tipo_contribuyente == "Moral":
            self.fields["escritura_numero_arrendatario"] = forms.CharField(
                label="Número Escritura Arrendatario", max_length=50
            )
            self.fields["escritura_fecha_arrendatario"] = forms.DateField(
                label="Fecha Escritura Arrendatario", widget=forms.DateInput(attrs={"type": "date"})
            )
            self.fields["notario_nombre_arrendatario"] = forms.CharField(
                label="Nombre Notario Arrendatario", max_length=100
            )
            self.fields["notario_numero_arrendatario"] = forms.CharField(
                label="Número Notario Arrendatario", max_length=50
            )
            self.fields["notario_ciudad_arrendatario"] = forms.CharField(
                label="Ciudad Notario Arrendatario", max_length=100
            )
            self.fields["apoderado_nombre_arrendatario"] = forms.CharField(
                label="Nombre Apoderado Arrendatario", max_length=100
            )
