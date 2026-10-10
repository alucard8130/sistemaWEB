"""App ``leasing``: segmento 'arrendamiento' de GESAC (ERP inmobiliario), modelos del MVP.

No confundir con la app existente ``arrendamientos`` (ContratoArea, áreas comunes
del segmento comercial): esa sigue intacta y no se toca.

Decisiones de diseño (ver INTEGRACION.md):
- Todo cuelga de ``empresa`` (multiempresa). Filtra SIEMPRE con ``.de_empresa(empresa)``.
- El contrato es versionado: las versiones nunca se sobrescriben.
- El sistema NO factura ni hace contabilidad por defecto: en La Comer la
  facturación mensual la dispara Oracle EBS. El calendario de rentas es
  "renta esperada" (control, alertas, proyección). El interruptor
  ``ConfiguracionArrendamiento.factura_en_sistema`` queda para otros clientes.
- Reglas legales/fiscales parametrizables (entidad federativa, uso), no fijas.
"""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone

EMPRESA_MODEL = getattr(settings, "GESAC_EMPRESA_MODEL", "empresas.Empresa")
USER_MODEL = settings.AUTH_USER_MODEL

SEGMENTO_ARRENDAMIENTO = "arrendamiento"


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def normalizar_cuenta_predial(valor: str) -> str:
    """Letras, guiones y otros símbolos se sustituyen por '0' (regla del SAT)."""
    return re.sub(r"[^0-9]", "0", (valor or "").strip())


def _mas_anios(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 de febrero
        return d.replace(year=d.year + n, day=28)


class EmpresaQuerySet(models.QuerySet):
    def de_empresa(self, empresa):
        return self.filter(empresa=empresa)


class EmpresaScopedModel(models.Model):
    empresa = models.ForeignKey(
        EMPRESA_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = EmpresaQuerySet.as_manager()

    class Meta:
        abstract = True


# --------------------------------------------------------------------------
# Configuración e integración con Oracle
# --------------------------------------------------------------------------
class ConfiguracionArrendamiento(EmpresaScopedModel):
    """Una fila por empresa con segmento 'arrendamiento'."""

    class SistemaExterno(models.TextChoices):
        NINGUNO = "NINGUNO", "Ninguno"
        ORACLE_EBS = "ORACLE_EBS", "Oracle E-Business Suite"

    empresa = models.OneToOneField(
        EMPRESA_MODEL, on_delete=models.PROTECT, related_name="config_arrendamiento"
    )
    factura_en_sistema = models.BooleanField(
        default=False,
        help_text="Si es False, la facturación la hace un sistema externo (p. ej. Oracle EBS).",
    )
    sistema_externo = models.CharField(
        max_length=20, choices=SistemaExterno.choices, default=SistemaExterno.NINGUNO
    )
    dias_alerta_default = models.PositiveIntegerField(default=90)

    class Meta:
        verbose_name = "configuración de arrendamiento"
        verbose_name_plural = "configuraciones de arrendamiento"


class SincronizacionExterna(EmpresaScopedModel):
    """Bitácora de cargas/sincronizaciones con el sistema externo (Oracle EBS)."""

    class Estado(models.TextChoices):
        OK = "OK", "Correcta"
        PARCIAL = "PARCIAL", "Con advertencias"
        ERROR = "ERROR", "Con error"

    sistema = models.CharField(max_length=20, default="ORACLE_EBS")
    entidad = models.CharField(max_length=40, help_text="contratos, locales, clientes, rentas…")
    estado = models.CharField(max_length=10, choices=Estado.choices)
    registros_leidos = models.PositiveIntegerField(default=0)
    registros_creados = models.PositiveIntegerField(default=0)
    registros_actualizados = models.PositiveIntegerField(default=0)
    registros_con_error = models.PositiveIntegerField(default=0)
    detalle = models.JSONField(default=dict, blank=True)
    iniciado_en = models.DateTimeField(default=timezone.now)
    terminado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-iniciado_en"]


# --------------------------------------------------------------------------
# Núcleo: contrapartes, inmuebles, unidades
# --------------------------------------------------------------------------
class Contraparte(EmpresaScopedModel):
    class Tipo(models.TextChoices):
        PF = "PF", "Persona física"
        PM = "PM", "Persona moral"

    tipo = models.CharField(max_length=2, choices=Tipo.choices)
    razon_social = models.CharField(max_length=255)
    rfc = models.CharField(max_length=13)
    regimen_fiscal = models.CharField(max_length=3, blank=True, help_text="Clave SAT (601, 606, 626…)")
    cp_fiscal = models.CharField(max_length=5, blank=True)
    uso_cfdi = models.CharField(max_length=4, default="G03")
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    representante_legal = models.CharField(max_length=255, blank=True)
    oracle_customer_id = models.CharField(max_length=40, blank=True, db_index=True)
    cliente = models.ForeignKey(
        "clientes.Cliente", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="contrapartes_leasing",
        help_text="Opcional: enlace al Cliente de GESAC si este sistema también factura/cobra.",
    )
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="contrapartes_leasing",
        help_text="Opcional: enlace al Proveedor de GESAC (p. ej. arrendador al que se le paga).",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["empresa", "rfc"],
                condition=~Q(rfc__in=["XAXX010101000", "XEXX010101000"]),
                name="uq_contraparte_empresa_rfc",
            )
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.rfc})"


class Inmueble(EmpresaScopedModel):
    clave = models.CharField(max_length=30)
    nombre = models.CharField(max_length=255)
    direccion = models.TextField(blank=True)
    entidad_federativa = models.CharField(
        max_length=60, help_text="Define la legislación civil aplicable."
    )
    folio_real = models.CharField(max_length=60, blank=True)
    propietario = models.ForeignKey(
        Contraparte, null=True, blank=True, on_delete=models.SET_NULL, related_name="inmuebles"
    )
    tiene_gravamen = models.BooleanField(default=False)
    gravamen_vigente_hasta = models.DateField(null=True, blank=True)
    oracle_location_id = models.CharField(max_length=40, blank=True, db_index=True)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["empresa", "clave"], name="uq_inmueble_empresa_clave")
        ]

    def __str__(self):
        return f"{self.clave} · {self.nombre}"


class CuentaPredial(EmpresaScopedModel):
    inmueble = models.ForeignKey(Inmueble, on_delete=models.CASCADE, related_name="cuentas_prediales")
    numero = models.CharField(max_length=40)
    numero_normalizado = models.CharField(max_length=40, editable=False)
    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "cuentas prediales"

    def save(self, *args, **kwargs):
        self.numero_normalizado = normalizar_cuenta_predial(self.numero)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero


class Unidad(EmpresaScopedModel):
    class Tipo(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        ISLA = "ISLA", "Isla / espacio comercial"
        BODEGA = "BODEGA", "Bodega"
        OFICINA = "OFICINA", "Oficina"
        ESTACIONAMIENTO = "ESTACIONAMIENTO", "Estacionamiento"
        OTRO = "OTRO", "Otro"

    class Uso(models.TextChoices):
        COMERCIAL = "COMERCIAL", "Comercial"
        HABITACIONAL = "HABITACIONAL", "Habitacional"
        MIXTO = "MIXTO", "Mixto"

    class Estatus(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        RENTADA = "RENTADA", "Rentada"
        SUBARRENDADA = "SUBARRENDADA", "Subarrendada"
        MANTENIMIENTO = "MANTENIMIENTO", "En mantenimiento"

    inmueble = models.ForeignKey(Inmueble, on_delete=models.PROTECT, related_name="unidades")
    clave = models.CharField(max_length=30)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.LOCAL)
    uso = models.CharField(max_length=15, choices=Uso.choices, default=Uso.COMERCIAL)
    m2_rentables = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    m2_utiles = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    m2_comunes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estatus = models.CharField(max_length=15, choices=Estatus.choices, default=Estatus.DISPONIBLE)
    cuentas_prediales = models.ManyToManyField(CuentaPredial, blank=True, related_name="unidades")
    oracle_location_id = models.CharField(max_length=40, blank=True, db_index=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["inmueble", "clave"], name="uq_unidad_inmueble_clave")
        ]

    def __str__(self):
        return f"{self.inmueble.clave}-{self.clave}"


# --------------------------------------------------------------------------
# Contrato y versiones
# --------------------------------------------------------------------------
class Contrato(EmpresaScopedModel):
    class Rol(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso (soy arrendador)"
        EGRESO = "EGRESO", "Egreso (soy arrendatario)"
        SUBARRIENDO = "SUBARRIENDO", "Subarriendo (ingreso ligado a un maestro)"

    class Tipo(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        ESPACIO_COMERCIAL = "ESPACIO_COMERCIAL", "Espacio comercial (isla)"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ACTIVO = "ACTIVO", "Activo"
        EN_RENOVACION = "EN_RENOVACION", "En renovación"
        TERMINADO = "TERMINADO", "Terminado"

    folio = models.CharField(max_length=40)
    rol = models.CharField(max_length=12, choices=Rol.choices)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.LOCAL)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    entidad_federativa = models.CharField(
        max_length=60, blank=True, help_text="Legislación aplicable; por defecto la del inmueble."
    )
    moneda = models.CharField(max_length=3, default="MXN")
    oracle_contract_id = models.CharField(max_length=40, blank=True, db_index=True)
    notas = models.TextField(blank=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["empresa", "folio"], name="uq_contrato_empresa_folio")
        ]
        indexes = [models.Index(fields=["empresa", "estado"])]  # noqa: RUF012

    def __str__(self):
        return f"{self.folio} ({self.get_rol_display()})"

    @property
    def version_vigente(self):
        return self.versiones.filter(es_vigente=True).first()

    @property
    def maestro(self):
        rel = getattr(self, "relacion_maestro", None)
        return rel.maestro if rel else None

    def puede_activarse(self):
        """Un contrato no se activa sin documento firmado en su versión vigente."""
        v = self.version_vigente
        if v is None:
            return False, "El contrato no tiene versión vigente."
        ok = v.documentos.filter(categoria=Documento.Categoria.CONTRATO_FIRMADO, firmado=True).exists()
        if not ok:
            return False, "Falta el documento de contrato firmado en la versión vigente."
        return True, ""

    def activar(self):
        ok, motivo = self.puede_activarse()
        if not ok:
            raise ValidationError(motivo)
        self.estado = self.Estado.ACTIVO
        self.save(update_fields=["estado", "actualizado_en"])


class ContratoParte(EmpresaScopedModel):
    class RolParte(models.TextChoices):
        ARRENDADOR = "ARRENDADOR", "Arrendador"
        ARRENDATARIO = "ARRENDATARIO", "Arrendatario"
        FIADOR = "FIADOR", "Fiador"
        OBLIGADO_SOLIDARIO = "OBLIGADO_SOLIDARIO", "Obligado solidario / aval"

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="partes")
    contraparte = models.ForeignKey(Contraparte, on_delete=models.PROTECT, related_name="participaciones")
    rol_parte = models.CharField(max_length=20, choices=RolParte.choices)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["contrato", "contraparte", "rol_parte"], name="uq_contrato_parte"
            )
        ]


class ContratoVersion(EmpresaScopedModel):
    class TipoEvento(models.TextChoices):
        ALTA = "ALTA", "Alta"
        CONVENIO = "CONVENIO", "Convenio modificatorio"
        PRORROGA = "PRORROGA", "Prórroga"
        RENOVACION = "RENOVACION", "Renovación"
        TERMINACION = "TERMINACION", "Terminación"

    class TipoVigencia(models.TextChoices):
        DETERMINADA = "DETERMINADA", "Determinada"
        INDETERMINADA = "INDETERMINADA", "Indeterminada"

    class Subarriendo(models.TextChoices):
        NO = "NO", "No permitido"
        GENERAL = "GENERAL", "Autorización general en el contrato"
        EXPRESO = "EXPRESO", "Requiere aprobación expresa"

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="versiones")
    numero = models.PositiveIntegerField()
    tipo_evento = models.CharField(max_length=15, choices=TipoEvento.choices, default=TipoEvento.ALTA)
    es_vigente = models.BooleanField(default=False)
    fecha_efectiva = models.DateField()
    fecha_firma = models.DateField(null=True, blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    tipo_vigencia = models.CharField(
        max_length=15, choices=TipoVigencia.choices, default=TipoVigencia.DETERMINADA
    )
    subarriendo_permitido = models.CharField(
        max_length=10, choices=Subarriendo.choices, default=Subarriendo.NO
    )
    anticipo_rentas_meses = models.PositiveIntegerField(default=0)
    inscribible = models.BooleanField(
        default=False, editable=False,
        help_text="Calculado: plazo > 6 años o anticipo de rentas > 3 años (art. 3042 CCF, validar por estado).",
    )
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["contrato", "numero"], name="uq_version_contrato_numero"),
            models.UniqueConstraint(
                fields=["contrato"], condition=Q(es_vigente=True), name="uq_version_vigente_por_contrato"
            ),
        ]
        ordering = ["contrato", "numero"]  # noqa: RUF012

    def __str__(self):
        return f"{self.contrato.folio} v{self.numero}"

    def clean(self):
        errores = {}
        if self.tipo_vigencia == self.TipoVigencia.DETERMINADA:
            if not self.fecha_fin:
                errores["fecha_fin"] = "La vigencia determinada requiere fecha de fin."
        elif self.fecha_fin:
            errores["fecha_fin"] = "La vigencia indeterminada no lleva fecha de fin."
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin <= self.fecha_inicio:
            errores["fecha_fin"] = "La fecha de fin debe ser posterior al inicio."
        if errores:
            raise ValidationError(errores)

    def _calcular_inscribible(self) -> bool:
        if self.anticipo_rentas_meses > 36:
            return True
        return bool(self.fecha_fin and self.fecha_fin > _mas_anios(self.fecha_inicio, 6))

    def save(self, *args, **kwargs):
        self.inscribible = self._calcular_inscribible()
        super().save(*args, **kwargs)

    @transaction.atomic
    def marcar_vigente(self):
        """Hace vigente esta versión y deja las demás del contrato como históricas."""
        ContratoVersion.objects.filter(contrato=self.contrato, es_vigente=True).exclude(
            pk=self.pk
        ).update(es_vigente=False)
        self.es_vigente = True
        self.save(update_fields=["es_vigente", "actualizado_en"])


class ContratoUnidad(EmpresaScopedModel):
    version = models.ForeignKey(ContratoVersion, on_delete=models.CASCADE, related_name="unidades")
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="contratos_versiones")
    m2_asignados = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["version", "unidad"], name="uq_version_unidad")
        ]


class RelacionMaestroSub(EmpresaScopedModel):
    """Vínculo back-to-back: un subarriendo (ingreso) ligado a su contrato maestro (egreso)."""

    class Consentimiento(models.TextChoices):
        GENERAL = "GENERAL", "Autorización general"
        EXPRESO = "EXPRESO", "Aprobación expresa del arrendador"

    sub = models.OneToOneField(Contrato, on_delete=models.CASCADE, related_name="relacion_maestro")
    maestro = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name="relaciones_sub")
    m2_asignados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_consentimiento = models.CharField(max_length=10, choices=Consentimiento.choices)
    documento_consentimiento = models.ForeignKey(
        "Documento", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def clean(self):
        if not (self.sub_id and self.maestro_id):
            return
        sub, maestro = self.sub, self.maestro
        errores = {}
        if sub.empresa_id != maestro.empresa_id:
            raise ValidationError("El subarriendo y el maestro deben ser de la misma empresa.")
        if sub.rol != Contrato.Rol.SUBARRIENDO:
            errores["sub"] = "El contrato debe tener rol SUBARRIENDO."
        if maestro.rol != Contrato.Rol.EGRESO:
            errores["maestro"] = "El contrato maestro debe tener rol EGRESO."
        vm, vs = maestro.version_vigente, sub.version_vigente
        if vm:
            if vm.subarriendo_permitido == ContratoVersion.Subarriendo.NO:
                errores["maestro"] = "El contrato maestro no permite subarriendo."
            if (
                vm.subarriendo_permitido == ContratoVersion.Subarriendo.EXPRESO
                and self.tipo_consentimiento != self.Consentimiento.EXPRESO
            ):
                errores["tipo_consentimiento"] = "El maestro exige aprobación expresa del arrendador."
            if vs and vm.fecha_fin and (vs.fecha_fin is None or vs.fecha_fin > vm.fecha_fin):
                errores["sub"] = "El subarriendo no puede exceder la vigencia del contrato maestro."
            disponible = vm.unidades.aggregate(t=Sum("m2_asignados"))["t"] or Decimal("0")  # noqa: FURB157
            otros = (
                RelacionMaestroSub.objects.filter(maestro=maestro).exclude(pk=self.pk)
                .aggregate(t=Sum("m2_asignados"))["t"] or Decimal("0")  # noqa: FURB157
            )
            if disponible and otros + self.m2_asignados > disponible:
                errores["m2_asignados"] = "Los m² subarrendados exceden los del contrato maestro."
        if self.tipo_consentimiento == self.Consentimiento.EXPRESO and not self.documento_consentimiento_id:
            errores["documento_consentimiento"] = "La aprobación expresa requiere el documento de consentimiento."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# --------------------------------------------------------------------------
# Términos financieros, escalador y calendario (renta esperada)
# --------------------------------------------------------------------------
class ConceptoCobro(EmpresaScopedModel):
    class Tipo(models.TextChoices):
        RENTA = "RENTA", "Renta"
        MANTENIMIENTO = "MANTENIMIENTO", "Mantenimiento"
        PUBLICIDAD = "PUBLICIDAD", "Publicidad"
        ESTACIONAMIENTO = "ESTACIONAMIENTO", "Estacionamiento"
        DEPOSITO = "DEPOSITO", "Depósito"
        PENALIDAD = "PENALIDAD", "Penalidad"
        OTRO = "OTRO", "Otro"

    clave = models.CharField(max_length=20)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.RENTA)
    clave_sat = models.CharField(max_length=10, default="80131502")
    unidad_sat = models.CharField(max_length=5, default="E48")
    tasa_iva = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.1600"))
    es_componente_arrendamiento = models.BooleanField(
        default=True, help_text="False para mantenimiento/servicios (separación NIF D-5)."
    )

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["empresa", "clave"], name="uq_concepto_empresa_clave")
        ]

    def __str__(self):
        return self.nombre


class TerminoFinanciero(EmpresaScopedModel):
    class Frecuencia(models.TextChoices):
        MENSUAL = "MENSUAL", "Mensual"
        BIMESTRAL = "BIMESTRAL", "Bimestral"
        TRIMESTRAL = "TRIMESTRAL", "Trimestral"
        SEMESTRAL = "SEMESTRAL", "Semestral"
        ANUAL = "ANUAL", "Anual"
        UNICA = "UNICA", "Única"

    MESES = {"MENSUAL": 1, "BIMESTRAL": 2, "TRIMESTRAL": 3, "SEMESTRAL": 6, "ANUAL": 12, "UNICA": 0}  # noqa: RUF012

    class MetodoPago(models.TextChoices):
        PUE = "PUE", "PUE"
        PPD = "PPD", "PPD"

    version = models.ForeignKey(ContratoVersion, on_delete=models.CASCADE, related_name="terminos")
    concepto = models.ForeignKey(ConceptoCobro, on_delete=models.PROTECT, related_name="terminos")
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    frecuencia = models.CharField(max_length=10, choices=Frecuencia.choices, default=Frecuencia.MENSUAL)
    dia_vencimiento = models.PositiveSmallIntegerField(default=1)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    metodo_pago = models.CharField(max_length=3, choices=MetodoPago.choices, default=MetodoPago.PPD)

    def clean(self):
        if not 1 <= self.dia_vencimiento <= 31:
            raise ValidationError({"dia_vencimiento": "Debe estar entre 1 y 31."})
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({"fecha_fin": "No puede ser anterior al inicio."})


class IndiceValor(models.Model):
    """Catálogo GLOBAL (sin empresa): valores del INPC u otros índices."""

    indice = models.CharField(max_length=20, default="INPC")
    periodo = models.DateField(help_text="Primer día del mes al que corresponde el valor.")
    valor = models.DecimalField(max_digits=14, decimal_places=6)
    base = models.CharField(max_length=40, default="2a. quincena jul 2018 = 100")
    fecha_publicacion_dof = models.DateField(null=True, blank=True)
    fuente = models.CharField(max_length=120, default="INEGI")

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["indice", "periodo"], name="uq_indice_periodo")
        ]
        ordering = ["indice", "-periodo"]  # noqa: RUF012

    def __str__(self):
        return f"{self.indice} {self.periodo:%Y-%m}: {self.valor}"


class Escalador(EmpresaScopedModel):
    class Tipo(models.TextChoices):
        INPC = "INPC", "Por INPC"
        FIJO_PCT = "FIJO_PCT", "Porcentaje fijo"
        MERCADO = "MERCADO", "A mercado (manual)"

    termino = models.ForeignKey(TerminoFinanciero, on_delete=models.CASCADE, related_name="escaladores")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    periodicidad_meses = models.PositiveIntegerField(default=12)
    aplicar_desde = models.DateField()
    rezago_meses = models.PositiveIntegerField(
        default=1, help_text="Meses antes del aniversario del que se toma el INPC final."
    )
    porcentaje_fijo = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    piso_pct = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    tope_pct = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)

    def clean(self):
        if self.tipo == self.Tipo.FIJO_PCT and self.porcentaje_fijo is None:
            raise ValidationError({"porcentaje_fijo": "El escalador fijo requiere porcentaje."})
        if self.piso_pct is not None and self.tope_pct is not None and self.piso_pct > self.tope_pct:
            raise ValidationError({"piso_pct": "El piso no puede ser mayor que el tope."})


class PartidaCalendario(EmpresaScopedModel):
    """Renta esperada por periodo. Por defecto NO genera facturas (ver docstring del módulo)."""

    class Estado(models.TextChoices):
        PROYECTADA = "PROYECTADA", "Proyectada"
        APROBADA = "APROBADA", "Aprobada"
        FACTURADA = "FACTURADA", "Facturada"
        COBRADA = "COBRADA", "Cobrada / pagada"
        CANCELADA = "CANCELADA", "Cancelada"

    class Origen(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        AJUSTE = "AJUSTE", "Ajuste"
        RETROACTIVO = "RETROACTIVO", "Retroactivo"

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="partidas")
    termino = models.ForeignKey(TerminoFinanciero, on_delete=models.PROTECT, related_name="partidas")
    periodo = models.DateField()
    fecha_vencimiento = models.DateField()
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROYECTADA)
    origen = models.CharField(max_length=12, choices=Origen.choices, default=Origen.NORMAL)
    creado_por = models.ForeignKey(
        USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    aprobada_por = models.ForeignKey(
        USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    aprobada_en = models.DateTimeField(null=True, blank=True)
    referencia_externa = models.CharField(
        max_length=60, blank=True, help_text="Folio de factura/cargo en Oracle EBS u otro sistema."
    )

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["termino", "periodo"],
                condition=Q(origen="NORMAL"),
                name="uq_partida_normal_termino_periodo",
            )
        ]
        indexes = [models.Index(fields=["empresa", "estado", "fecha_vencimiento"])]  # noqa: RUF012
        ordering = ["fecha_vencimiento"]  # noqa: RUF012

    def aprobar(self, usuario):
        if self.estado != self.Estado.PROYECTADA:
            raise ValidationError("Solo se aprueban partidas proyectadas.")
        if self.creado_por_id and self.creado_por_id == usuario.pk:
            raise ValidationError("Segregación de funciones: quien crea la partida no la aprueba.")
        self.estado = self.Estado.APROBADA
        self.aprobada_por = usuario
        self.aprobada_en = timezone.now()
        self.save(update_fields=["estado", "aprobada_por", "aprobada_en", "actualizado_en"])


# --------------------------------------------------------------------------
# Garantías, obligaciones y opciones
# --------------------------------------------------------------------------
class Garantia(EmpresaScopedModel):
    class Tipo(models.TextChoices):
        DEPOSITO = "DEPOSITO", "Depósito en garantía"
        FIANZA = "FIANZA", "Fianza"
        CARTA_CREDITO = "CARTA_CREDITO", "Carta de crédito"
        AVAL = "AVAL", "Aval"
        SEGURO = "SEGURO", "Seguro"

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="garantias")
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    emisor = models.CharField(max_length=255, blank=True, help_text="Afianzadora o aseguradora.")
    poliza = models.CharField(max_length=60, blank=True)
    vigencia_inicio = models.DateField(null=True, blank=True)
    vigencia_fin = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)


class Obligacion(EmpresaScopedModel):
    """Fecha clave con alerta: seguros, fianzas, avisos, inscripción RPP, revisiones de renta…"""

    class Tipo(models.TextChoices):
        SEGURO = "SEGURO", "Seguro"
        FIANZA = "FIANZA", "Fianza"
        AVISO = "AVISO", "Aviso"
        INSCRIPCION_RPP = "INSCRIPCION_RPP", "Inscripción en Registro Público"
        REVISION_RENTA = "REVISION_RENTA", "Revisión de renta"
        RENOVACION = "RENOVACION", "Renovación"
        ENTREGA = "ENTREGA", "Entrega de local"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CUMPLIDA = "CUMPLIDA", "Cumplida"
        VENCIDA = "VENCIDA", "Vencida"
        CANCELADA = "CANCELADA", "Cancelada"

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="obligaciones")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha_limite = models.DateField()
    dias_anticipacion_alerta = models.PositiveIntegerField(default=90)
    responsable = models.ForeignKey(
        USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    evidencia = models.ForeignKey(
        "Documento", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [models.Index(fields=["empresa", "estado", "fecha_limite"])]  # noqa: RUF012
        ordering = ["fecha_limite"]  # noqa: RUF012


class Opcion(EmpresaScopedModel):
    class Tipo(models.TextChoices):
        RENOVACION = "RENOVACION", "Renovación"
        TERMINACION_ANTICIPADA = "TERMINACION_ANTICIPADA", "Terminación anticipada"
        PREFERENCIA = "PREFERENCIA", "Derecho de preferencia"
        EXPANSION = "EXPANSION", "Expansión"

    class Decision(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EJERCIDA = "EJERCIDA", "Ejercida"
        NO_EJERCIDA = "NO_EJERCIDA", "No ejercida"

    version = models.ForeignKey(ContratoVersion, on_delete=models.CASCADE, related_name="opciones")
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    ventana_inicio = models.DateField(null=True, blank=True)
    ventana_fin = models.DateField(null=True, blank=True)
    fecha_limite_aviso = models.DateField()
    penalidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    decision = models.CharField(max_length=12, choices=Decision.choices, default=Decision.PENDIENTE)


# --------------------------------------------------------------------------
# Expediente digital
# --------------------------------------------------------------------------
def _ruta_documento(instance, filename):
    return f"leasing/{instance.empresa_id}/{instance.contrato_id}/{filename}"


class Documento(EmpresaScopedModel):
    class Categoria(models.TextChoices):
        CONTRATO_FIRMADO = "CONTRATO_FIRMADO", "Contrato firmado"
        CONVENIO = "CONVENIO", "Convenio modificatorio"
        CONSENTIMIENTO_SUBARRIENDO = "CONSENTIMIENTO_SUBARRIENDO", "Consentimiento de subarriendo"
        GARANTIA = "GARANTIA", "Garantía / póliza"
        AVISO = "AVISO", "Aviso / notificación"
        ACTA_ENTREGA = "ACTA_ENTREGA", "Acta de entrega"
        IDENTIFICACION = "IDENTIFICACION", "Identificación / personalidad"
        OTRO = "OTRO", "Otro"

    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name="documentos")
    version = models.ForeignKey(
        ContratoVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="documentos"
    )
    categoria = models.CharField(max_length=30, choices=Categoria.choices, default=Categoria.OTRO)
    titulo = models.CharField(max_length=255, blank=True)
    archivo = models.FileField(upload_to=_ruta_documento)
    sha256 = models.CharField(max_length=64, editable=False, blank=True)
    firmado = models.BooleanField(default=False)
    proveedor_firma = models.CharField(max_length=60, blank=True)
    constancia_nom151 = models.FileField(upload_to=_ruta_documento, null=True, blank=True)
    retener_hasta = models.DateField(null=True, blank=True)
    subido_por = models.ForeignKey(
        USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def save(self, *args, **kwargs):
        if self.archivo and not self.sha256:
            h = hashlib.sha256()
            for chunk in self.archivo.chunks():
                h.update(chunk)
            self.sha256 = h.hexdigest()
        super().save(*args, **kwargs)


# --------------------------------------------------------------------------
# Mantenimiento, proveedores y presupuesto
# --------------------------------------------------------------------------
class Incidencia(EmpresaScopedModel):
    """Incidencia / orden de mantenimiento; el gasto se clasifica capex u opex."""

    class Tipo(models.TextChoices):
        FILTRACION = "FILTRACION", "Filtración de agua"
        ELECTRICO = "ELECTRICO", "Eléctrico"
        HIDRAULICO = "HIDRAULICO", "Hidráulico"
        AIRE = "AIRE", "Aire acondicionado"
        ESTRUCTURA = "ESTRUCTURA", "Estructura / obra civil"
        LIMPIEZA = "LIMPIEZA", "Limpieza"
        SEGURIDAD = "SEGURIDAD", "Seguridad"
        OTRO = "OTRO", "Otro"

    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CERRADA = "CERRADA", "Cerrada"
        CANCELADA = "CANCELADA", "Cancelada"

    class Naturaleza(models.TextChoices):
        CAPEX = "CAPEX", "Capex"
        OPEX = "OPEX", "Opex"

    class Ejecutor(models.TextChoices):
        INTERNO = "INTERNO", "Personal interno"
        PROVEEDOR = "PROVEEDOR", "Proveedor externo"

    class Responsable(models.TextChoices):
        ARRENDADOR = "ARRENDADOR", "Arrendador"
        ARRENDATARIO = "ARRENDATARIO", "Arrendatario"
        COMPARTIDO = "COMPARTIDO", "Compartido"

    inmueble = models.ForeignKey(Inmueble, on_delete=models.PROTECT, related_name="incidencias")
    unidad = models.ForeignKey(Unidad, null=True, blank=True, on_delete=models.SET_NULL, related_name="incidencias")
    contrato = models.ForeignKey(Contrato, null=True, blank=True, on_delete=models.SET_NULL, related_name="incidencias")
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.OTRO)
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ABIERTA)
    naturaleza_gasto = models.CharField(max_length=5, choices=Naturaleza.choices, default=Naturaleza.OPEX)
    ejecutor = models.CharField(max_length=10, choices=Ejecutor.choices, default=Ejecutor.INTERNO)
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incidencias_leasing",
        help_text="Proveedor de GESAC (limpieza, seguridad, mantenimiento…). Ahí vive su REPSE.",
    )
    gasto = models.ForeignKey(
        "gastos.Gasto", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incidencias_leasing",
        help_text="Gasto registrado en el módulo de Gastos: de ahí salen presupuesto vs real y pólizas.",
    )
    tipo_gasto = models.ForeignKey(
        "gastos.TipoGasto", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incidencias_leasing",
    )
    responsable_costo = models.CharField(max_length=15, choices=Responsable.choices, default=Responsable.ARRENDADOR)
    recuperable = models.BooleanField(default=False, help_text="Recuperable al arrendatario (base de la futura conciliación CAM).")
    descripcion = models.TextField()
    costo_estimado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    costo_real = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fecha_reporte = models.DateField(default=date.today)
    fecha_cierre = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["empresa", "estado", "prioridad"])]  # noqa: RUF012
        ordering = ["-fecha_reporte"]  # noqa: RUF012


class PresupuestoMantenimiento(EmpresaScopedModel):
    """Presupuesto de mantenimiento POR INMUEBLE (capex/opex).

    ``presupuestos.Presupuesto`` de GESAC es por empresa/tipo de gasto/mes y no tiene
    dimensión de inmueble; esta tabla la complementa sin sustituirla.
    """

    inmueble = models.ForeignKey(Inmueble, on_delete=models.PROTECT, related_name="presupuestos")
    anio = models.PositiveSmallIntegerField()
    naturaleza_gasto = models.CharField(max_length=5, choices=Incidencia.Naturaleza.choices)
    monto_presupuestado = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["empresa", "inmueble", "anio", "naturaleza_gasto"],
                name="uq_presupuesto_mant",
            )
        ]


# --------------------------------------------------------------------------
# Bitácora de auditoría (append-only, hashes encadenados)
# --------------------------------------------------------------------------
class _SoloAnexarQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("La bitácora de auditoría es de solo anexar.")

    def delete(self):
        raise RuntimeError("La bitácora de auditoría es de solo anexar.")


class BitacoraAuditoria(models.Model):
    empresa = models.ForeignKey(
        EMPRESA_MODEL, on_delete=models.PROTECT, related_name="%(app_label)s_bitacora_set"
    )
    usuario = models.ForeignKey(USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    accion = models.CharField(max_length=40)
    entidad = models.CharField(max_length=60)
    entidad_id = models.CharField(max_length=40)
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(default=timezone.now)
    hash_previo = models.CharField(max_length=64, blank=True, editable=False)
    hash_registro = models.CharField(max_length=64, blank=True, editable=False)

    objects = _SoloAnexarQuerySet.as_manager()

    class Meta:
        ordering = ["id"]  # noqa: RUF012
        indexes = [models.Index(fields=["empresa", "entidad", "entidad_id"])]  # noqa: RUF012

    def _payload(self) -> str:
        return json.dumps(
            {
                "empresa": self.empresa_id,
                "usuario": self.usuario_id,
                "accion": self.accion,
                "entidad": self.entidad,
                "entidad_id": self.entidad_id,
                "anterior": self.valor_anterior,
                "nuevo": self.valor_nuevo,
                "motivo": self.motivo,
                "ip": self.ip,
                "creado_en": self.creado_en.isoformat(),
                "hash_previo": self.hash_previo,
            },
            sort_keys=True,
            default=str,
        )

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("La bitácora de auditoría es de solo anexar.")
        ultimo = (
            BitacoraAuditoria.objects.select_for_update()
            .filter(empresa_id=self.empresa_id)
            .order_by("-id")
            .first()
        )
        self.hash_previo = ultimo.hash_registro if ultimo else ""
        self.hash_registro = hashlib.sha256(self._payload().encode()).hexdigest()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("La bitácora de auditoría es de solo anexar.")

    @classmethod
    def verificar_cadena(cls, empresa) -> bool:
        previo = ""
        for reg in cls.objects.filter(empresa=empresa).order_by("id"):
            if reg.hash_previo != previo:
                return False
            if hashlib.sha256(reg._payload().encode()).hexdigest() != reg.hash_registro:
                return False
            previo = reg.hash_registro
        return True
