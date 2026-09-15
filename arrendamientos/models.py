from django.conf import settings
from django.db import models
from django.utils import timezone  # noqa: F401


class ContratoArea(models.Model):
    """Un contrato de arrendamiento de un area comun -- un area puede
    tener varios a lo largo del tiempo (historial completo). El
    contrato vigente sincroniza sus datos clave hacia AreaComun, para
    que la facturacion mensual siga funcionando sin cambios."""

    area = models.ForeignKey('areas.AreaComun', on_delete=models.CASCADE, related_name='contratos')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='contratos_areas')

    fecha_firma = models.DateField(
        help_text="Fecha en que se firmó el contrato -- puede ser anterior a fecha_inicio."
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    cuota = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Renta fija, o renta base si tipo_renta es 'mixta'. Renta mínima "
                   "garantizada (o $0) si tipo_renta es 'variable'."
    )
    deposito = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    giro = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Giro comercial del arrendatario -- ej. restaurante, ropa, servicios."
    )

    ESTATUS_CHOICES = [  # noqa: RUF012
        ('vigente', 'Vigente'),
        ('renovado', 'Renovado (ya existe uno nuevo)'),
        ('vencido_ocupado', 'Vencido -- Ocupado (mes a mes)'),
        ('terminado', 'Terminado sin renovar'),
    ]
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='vigente')

    plazo_forzoso_meses = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Meses durante los cuales el arrendatario NO puede rescindir sin penalizacion -- "
                   "vinculado con fecha_inicio/fecha_fin (captura cualquiera de los 2, el otro se calcula solo)."
    )
    renovacion_automatica = models.BooleanField(
        default=False, verbose_name="¿Renovación automática al vencer?",
        help_text="Si está activo (junto con tipo_incremento='porcentaje_fijo'), habilita el botón "
                   "de un clic 'Renovar con % pactado' en Gestión de Contratos."
    )

    TIPO_INCREMENTO_CHOICES = [  # noqa: RUF012
        ('ninguno', 'Sin incremento pactado'),
        ('porcentaje_fijo', 'Porcentaje fijo'),
        ('inpc', 'Indexado a INPC'),
    ]
    tipo_incremento = models.CharField(max_length=20, choices=TIPO_INCREMENTO_CHOICES, default='ninguno')
    porcentaje_incremento = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
        help_text="% pactado en el contrato (si el tipo es porcentaje fijo)."
    )

    PERIODICIDAD_CHOICES = [  # noqa: RUF012
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]
    periodicidad_facturacion = models.CharField(
        max_length=20, choices=PERIODICIDAD_CHOICES, default='mensual'
    )

    TIPO_RENTA_CHOICES = [  # noqa: RUF012
        ('fija', 'Fija'),
        ('variable', 'Variable (% sobre ventas)'),
        ('mixta', 'Mixta (renta base + % sobre ventas)'),
    ]
    tipo_renta = models.CharField(max_length=20, choices=TIPO_RENTA_CHOICES, default='fija')
    porcentaje_ventas = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
        help_text="% sobre ventas netas del arrendatario -- aplica si tipo_renta es 'variable' o 'mixta'."
    )

    incluye_mantenimiento = models.BooleanField(
        default=False, verbose_name="¿Incluye cuota de mantenimiento?",
        help_text="Cargo aparte, independiente del tipo de renta -- se puede activar junto "
                   "con renta fija, variable, o mixta."
    )
    cuota_mantenimiento = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text="Monto del cargo de mantenimiento -- aplica si incluye_mantenimiento está activo."
    )

    penalizacion_atraso_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
        help_text="% de recargo por atraso en el pago, según contrato."
    )

    ESTATUS_DEPOSITO_CHOICES = [  # noqa: RUF012
        ('retenido', 'Retenido'),
        ('devuelto', 'Devuelto'),
        ('aplicado_danos', 'Aplicado a daños'),
        ('aplicado_adeudos', 'Aplicado a rentas'),
    ]
    estatus_deposito = models.CharField(
        max_length=20, choices=ESTATUS_DEPOSITO_CHOICES, default='retenido', blank=True, null=True
    )

    clausulas_especiales = models.TextField(
        blank=True, null=True,
        help_text="Exclusividad de zona, restricciones de uso, u otras condiciones especiales."
    )

    contrato_pdf = models.FileField(
        upload_to='contratos_areas/', blank=True, null=True,
        help_text="Documento del contrato de arrendamiento firmado -- opcional."
    )

    contrato_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='renovaciones',
        help_text="Si este contrato es una renovación de uno anterior, apunta hacia él."
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )





    class Meta:
        ordering = ['-fecha_inicio']  # noqa: RUF012

    def __str__(self):
        return f"Contrato {self.area.numero} ({self.fecha_inicio} - {self.fecha_fin})"

    @property
    def dias_gracia(self):
        """Dias entre la firma y el arranque real del contrato (y de su
        facturacion) -- tiempo que el arrendatario tiene, por ejemplo,
        para remodelar antes de empezar a pagar renta."""
        if self.fecha_firma and self.fecha_inicio:
            return (self.fecha_inicio - self.fecha_firma).days
        return 0

    # @property
    # def esta_vencido(self):
    #     """True si el contrato sigue marcado como 'vigente' en el
    #     sistema, pero su fecha_fin ya paso -- senal de que necesita
    #     renovarse o terminarse desde Gestion de Contratos."""
    #     return self.estatus == 'vigente' and self.fecha_fin < timezone.now().date()

    def sincronizar_a_area(self):
        """Empuja los datos de este contrato hacia el AreaComun, para
        que la facturacion mensual (que lee area.cuota, area.cliente,
        etc. directo) siga funcionando sin tocarla."""
        self.area.cliente = self.cliente
        self.area.giro = self.giro

        if self.tipo_renta == 'fija' and self.incluye_mantenimiento and self.cuota_mantenimiento:
            self.area.cuota = self.cuota + self.cuota_mantenimiento
        else:
            self.area.cuota = self.cuota

        self.area.deposito = self.deposito
        self.area.fecha_inicial = self.fecha_inicio
        self.area.fecha_fin = self.fecha_fin
        self.area.status = 'ocupado'

        self.area.es_cuota_anual = (self.periodicidad_facturacion == 'anual')
        self.area.es_cuota_variable = (self.tipo_renta in ('variable', 'mixta'))
        self.area.periodicidad_facturacion = self.periodicidad_facturacion

        self.area.save(update_fields=[
            'cliente', 'giro', 'cuota', 'deposito', 'fecha_inicial', 'fecha_fin', 'status',
            'es_cuota_anual', 'es_cuota_variable', 'periodicidad_facturacion',
        ])


class ReporteVentasContrato(models.Model):
    """Captura de ventas de un periodo (mensual, semestral, etc.) para
    calcular la parte variable de la renta -- un contrato de renta
    fija nunca genera registros aqui."""

    contrato = models.ForeignKey(ContratoArea, on_delete=models.CASCADE, related_name='reportes_ventas')
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    monto_ventas = models.DecimalField(max_digits=12, decimal_places=2)

    porcentaje_aplicado = models.DecimalField(max_digits=5, decimal_places=2)
    renta_variable_calculada = models.DecimalField(max_digits=10, decimal_places=2)
    renta_base_del_periodo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_a_cobrar = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_captura = models.DateTimeField(auto_now_add=True)
    capturado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-periodo_inicio']  # noqa: RUF012

    def __str__(self):
        return f"Ventas {self.contrato.area.numero} {self.periodo_inicio}—{self.periodo_fin}: ${self.monto_ventas}"
