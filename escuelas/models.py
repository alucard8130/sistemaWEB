from decimal import Decimal

from django.conf import settings
from django.db import models


class IngresoEscuela(models.Model):
    """Ingresos importados desde un Excel externo (ej. Academic+ Control)
    -- ligeros, sin cliente ni factura, solo para alimentar graficos y
    comparativos de Tesoreria/Presupuestos en el mini ERP de escuelas."""

    CATEGORIA_CHOICES = [  # noqa: RUF012
        ('colegiatura', 'Colegiatura'),
        ('inscripcion', 'Inscripción'),
        ('otro', 'Otro'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='ingresos_escuela')
    fecha = models.DateField()
    concepto = models.CharField(max_length=255)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro')
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    fecha_importacion = models.DateTimeField(auto_now_add=True)
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    archivo_origen = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Nombre del archivo Excel del que se importó, para rastrear el origen."
    )
    # NUEVO -- capturados directo del Excel real de Academic+
    forma_pago = models.CharField(max_length=50, blank=True, null=True)
    alumno = models.CharField(max_length=255, blank=True, null=True)

    # NUEVO -- matricula del alumno (clave real para rastrear alumnos
    # unicos entre distintos archivos e importaciones) y de donde vino
    # el registro (util para depurar o filtrar por fuente).
    ORIGEN_CHOICES = [  # noqa: RUF012
        ('cobranza', 'Reporte de Cobranza'),
        ('fiserv', 'Plataforma Academic (Fiserv)'),
    ]
    matricula = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, blank=True, null=True)

    # NUEVO -- comision que descuenta el comisionista de la plataforma
    # (solo aplica a origen='fiserv'). Se guarda el % realmente aplicado
    # en cada registro -- asi, si el % se corrige mas adelante, los
    # registros ya importados conservan el que se les aplico en su
    # momento, sin quedar inconsistentes entre si.
    comision = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))  # noqa: FURB157
    porcentaje_comision_aplicado = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="% de comision aplicado a este registro en el momento de importarlo."
    )


    # ------------------------------------------------------------------
    # NUEVO -- Detalle de Pagos de Academic+ (IPC, Cafeteria, Colegiaturas)
    # ------------------------------------------------------------------
    FUENTE_CHOICES = [  # noqa: RUF012
        ('ipc', 'IPC (cursos, talleres, transporte, uniformes)'),
        ('cafeteria', 'Cafetería'),
        ('colegiaturas', 'Colegiaturas / inscripciones'),
    ]
    recibo = models.CharField(max_length=30, blank=True, null=True, db_index=True)
    nivel = models.CharField(max_length=30, blank=True, default='')
    grado = models.CharField(max_length=30, blank=True, default='')
    grupo = models.CharField(max_length=30, blank=True, default='')
    # Concepto "limpio" (sin mes, ciclo, talla ni zona) para reportes por categoria.
    rubro = models.CharField(max_length=60, blank=True, default='', db_index=True)
    fuente = models.CharField(max_length=20, choices=FUENTE_CHOICES, blank=True, default='')
    # Efectivo NUNCA pasa por bancos: va a un fondeo de caja chica.
    es_efectivo = models.BooleanField(default=False, db_index=True)
    # Banco donde cayo el ingreso (solo cuando NO es efectivo). Ingreso al 100%;
    # la comision se registra a mano como gasto.
    cuenta_bancaria = models.ForeignKey(
        'empresas.CuentaBancaria', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ingresos_escuela',
    )
    # Fondeo de caja chica al que se sumo este cobro en efectivo.
    fondeo = models.ForeignKey(
        'caja_chica.FondeoCajaChica', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ingresos_escuela',
    )
    lote = models.ForeignKey(
        'LoteImportacionIngresos', on_delete=models.CASCADE, null=True, blank=True,
        related_name='ingresos',
    )
    # Huella de la fila (recibo+matricula+concepto+importe+fecha+n.o de
    # ocurrencia) para que re-subir el mismo archivo NO duplique ingresos.
    clave_unica = models.CharField(max_length=40, blank=True, null=True)

    class Meta:
        ordering = ['-fecha']  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=['empresa', 'clave_unica'], name='uniq_ingreso_escuela_clave'
            ),
        ]


    @property
    def monto_neto(self):
        """Lo que realmente entro a bancos, despues de la comision."""
        return self.monto - self.comision


    def __str__(self):
        return f"{self.fecha} -- {self.concepto}: ${self.monto}"


class LoteImportacionIngresos(models.Model):
    """Una subida de archivo 'Detalle de Pagos'. Sirve para auditar lo que
    entro y para poder deshacer la importacion completa."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='lotes_ingresos')
    fuente = models.CharField(max_length=20, choices=IngresoEscuela.FUENTE_CHOICES)
    archivo = models.CharField(max_length=255)
    cuenta_bancaria = models.ForeignKey(
        'empresas.CuentaBancaria', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lotes_ingresos_escuela',
    )
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    filas = models.PositiveIntegerField(default=0)
    filas_duplicadas = models.PositiveIntegerField(default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))  # noqa: FURB157
    total_efectivo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))  # noqa: FURB157
    total_banco = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))  # noqa: FURB157

    class Meta:
        ordering = ['-fecha_importacion']  # noqa: RUF012

    def __str__(self):
        return f"{self.archivo} ({self.get_fuente_display()}) -- ${self.total}"


### Modelos relacionados con solicitudes de admisión
class SolicitudAdmision(models.Model):
    """Solicitudes/prospectos del proceso de admision, sincronizadas
    desde el pipeline 'Admisiones' de HubSpot via webhook -- cada vez
    que un deal cambia de etapa (o se crea), HubSpot avisa a este
    sistema y este modelo se actualiza."""

    ETAPA_CHOICES = [  # noqa: RUF012
        ('prospecto', 'Prospecto'),
        ('contacto', 'Contacto'),
        ('visita_agendada', 'Visita agendada'),
        ('visita_realizada', 'Visita realizada'),
        ('solicitud', 'Solicitud'),
        ('inscrito', 'Inscrito'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='solicitudes_admision')

    hubspot_deal_id = models.CharField(max_length=50, unique=True, db_index=True)
    nombre_contacto = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    nivel_de_interes = models.CharField(max_length=100, blank=True, null=True)
    mensaje = models.TextField(blank=True, null=True)
    etapa = models.CharField(max_length=30, choices=ETAPA_CHOICES, default='prospecto')

    fecha_creacion_hubspot = models.DateTimeField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_recibido = models.DateTimeField(auto_now_add=True)

    payload_crudo = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_actualizacion']  # noqa: RUF012

    def __str__(self):
        return f"{self.nombre_contacto or self.hubspot_deal_id} -- {self.get_etapa_display()}"



class Alumno(models.Model):
    """Roster real de alumnos, importado periodicamente desde los
    reportes de Academic+ (Alumnos por Grupo, Altas por Ciclo). Cada
    vez que se importa el roster completo de un nivel, los alumnos que
    dejan de aparecer se marcan como inactivos (baja detectada)."""

    NIVEL_CHOICES = [  # noqa: RUF012
        ('preescolar', 'Preescolar'),
        ('primaria', 'Primaria'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='alumnos')
    matricula = models.CharField(max_length=20, db_index=True)
    nombre = models.CharField(max_length=255)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, blank=True, null=True)
    grado = models.CharField(max_length=50, blank=True, null=True)
    grupo = models.CharField(max_length=20, blank=True, null=True)
    turno = models.CharField(max_length=20, blank=True, null=True)

    fecha_alta = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_ultimo_visto = models.DateField(blank=True, null=True)
    fecha_baja_detectada = models.DateField(blank=True, null=True)

    fecha_importacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('empresa', 'matricula')]  # noqa: RUF012
        ordering = ['nivel', 'grado', 'grupo', 'nombre']  # noqa: RUF012

    def __str__(self):
        return f"{self.matricula} -- {self.nombre}"


class CarteraVencida(models.Model):
    """Saldos vencidos por alumno y concepto, importados desde el
    reporte de Deudores de Academic+ -- un solo archivo mensual, que
    ya trae todos los conceptos (colegiatura, inscripcion, talleres,
    etc.) desglosados. Cada import es un SNAPSHOT identificado por su
    fecha de corte, para poder comparar la cartera mes a mes."""

    CATEGORIA_CHOICES = [  # noqa: RUF012
        ('colegiatura', 'Colegiatura'),
        ('inscripcion', 'Inscripción'),
        ('otro', 'Otro'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='cartera_vencida')
    fecha_corte = models.DateField(db_index=True)

    matricula = models.CharField(max_length=20, db_index=True)
    nombre_alumno = models.CharField(max_length=255)
    grupo = models.CharField(max_length=20, blank=True, null=True)
    concepto = models.CharField(max_length=255)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro')
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    fecha_importacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_corte', '-monto']  # noqa: RUF012

    def __str__(self):
        return f"{self.nombre_alumno} -- {self.concepto} ({self.fecha_corte}): ${self.monto}"



class PresupuestoIngresoEscuela(models.Model):
    """Presupuesto mensual de ingresos, especifico para el ERP Escolar
    -- usa las mismas 3 categorias que ya usa IngresoEscuela (colegiatura,
    inscripcion, otro), sin el desglose de 'tipo_otro' que si necesita
    GESAC (aqui no aplica)."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='presupuestos_ingreso_escuela')
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField()
    categoria = models.CharField(max_length=20, choices=IngresoEscuela.CATEGORIA_CHOICES)
    monto_presupuestado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('empresa', 'anio', 'mes', 'categoria')

    def __str__(self):
        return f"{self.empresa} {self.get_categoria_display()} {self.mes}/{self.anio}: {self.monto_presupuestado}"