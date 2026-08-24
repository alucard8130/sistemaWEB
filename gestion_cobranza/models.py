
from decimal import Decimal
from functools import cached_property

from django.conf import settings
from django.core.serializers import json
from django.db import models
from django.utils import timezone

from facturacion.models import Factura

# ============================================================
# 1. Expediente de Cobranza -- un caso activo por cliente con deuda
# ============================================================

class ExpedienteCobranza(models.Model):
    ETAPA_CHOICES = [  # noqa: RUF012
        ('recordatorio', 'Recordatorio amistoso'),
        ('llamada', 'Llamada de seguimiento'),
        ('carta_intencion', 'Carta de intención'),
        ('carta_extrajudicial', 'Carta extrajudicial'),
        ('plan_pago', 'Plan de pago'),
        ('juridico', 'Turnado a jurídico'),
        ('cerrado', 'Cerrado / Resuelto'),
    ]
    ESTATUS_CHOICES = [  # noqa: RUF012
        ('activo', 'Activo'),
        ('cerrado', 'Cerrado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='expedientes_cobranza')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='expedientes_cobranza')

    etapa = models.CharField(max_length=25, choices=ETAPA_CHOICES, default='recordatorio')
    estatus = models.CharField(max_length=10, choices=ESTATUS_CHOICES, default='activo')

    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    motivo_cierre = models.CharField(max_length=255, blank=True, null=True)
    # NUEVO -- captura cuánto era el saldo vencido justo al momento de
    # cerrar el expediente. Necesario porque saldo_vencido_total siempre
    # se calcula EN VIVO contra las facturas actuales -- en cuanto el
    # cliente paga, esa información "desaparece" de ahí. Sin este campo,
    # no habría forma de reportar "cuánto se recuperó" en un periodo.
    monto_al_cierre = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Saldo vencido que tenía el expediente al momento de cerrarse."
    )

    asignado_a = models.ForeignKey(
        'empleados.Empleado', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='expedientes_asignados'
    )
    notas_generales = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_apertura']  # noqa: RUF012
        # Un cliente solo puede tener UN expediente activo a la vez -- si
        # se cierra y vuelve a caer en mora, se abre uno nuevo.
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=['empresa', 'cliente'],
                condition=models.Q(estatus='activo'),
                name='unico_expediente_activo_por_cliente',
            )
        ]

    def __str__(self):
        return f"Expediente #{self.id} — {self.cliente.nombre} ({self.get_etapa_display()})"

    # ---- Cálculos dinámicos de deuda -- NUNCA se guardan en snapshot,
    # siempre se recalculan al vuelo contra las facturas reales. ----

    def _facturas_vencidas_qs(self):
        hoy = timezone.now().date()
        return Factura.objects.filter(
            empresa=self.empresa, cliente=self.cliente, activo=True,
            estatus='pendiente', fecha_vencimiento__lt=hoy,
        ).select_related('local', 'area_comun').prefetch_related('pagos')

    # NUEVO -- versión CACHEADA de la misma consulta. Se ejecuta UNA sola
    # vez por expediente (por instancia de Python), sin importar cuántas
    # veces se lean saldo_vencido_total/dias_atraso_maximo/rango_antiguedad
    # en la misma request (ordenar, sumar, template...).
    @cached_property
    def _facturas_vencidas_lista(self):
        return list(self._facturas_vencidas_qs())

    @cached_property
    def saldo_vencido_total(self):
        return sum((Decimal(str(f.saldo_pendiente)) for f in self._facturas_vencidas_lista), Decimal("0"))

    @cached_property
    def dias_atraso_maximo(self):
        hoy = timezone.now().date()
        fechas = [f.fecha_vencimiento for f in self._facturas_vencidas_lista]
        if not fechas:
            return 0
        return (hoy - min(fechas)).days

    @property
    def rango_antiguedad(self):
        """0-30 / 31-60 / 61-90 / 90+ días -- para el dashboard/reportes."""
        dias = self.dias_atraso_maximo
        if dias <= 30:
            return '0-30'
        if dias <= 60:
            return '31-60'
        if dias <= 90:
            return '61-90'
        return '90+'

    def cerrar(self, motivo=""):
         # Captura el saldo ANTES de marcarlo cerrado -- mientras las
        # facturas vencidas de este cliente todavía se pueden consultar
        # con normalidad.
        self.monto_al_cierre = self.saldo_vencido_total
        self.estatus = 'cerrado'
        self.fecha_cierre = timezone.now()
        self.motivo_cierre = motivo
        self.save(update_fields=['estatus', 'fecha_cierre', 'motivo_cierre', 'monto_al_cierre'])


# ============================================================
# 2. Gestión de Cobranza -- bitácora de cada interacción
# ============================================================

class GestionCobranza(models.Model):
    TIPO_CHOICES = [  # noqa: RUF012
        ('llamada', 'Llamada telefónica'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Correo electrónico'),
        ('carta_extrajudicial', 'Carta extrajudicial'),
        ('visita', 'Visita presencial'),
        ('nota', 'Nota interna'),
    ]
    RESULTADO_CHOICES = [  # noqa: RUF012
        ('promesa_pago', 'Promesa de pago'),
        ('no_contesto', 'No contestó'),
        ('se_nego', 'Se negó a pagar'),
        ('numero_equivocado', 'Número/dato equivocado'),
        ('ya_pago', 'Ya había pagado'),
        ('pendiente_respuesta', 'Pendiente de respuesta'),
        ('otro', 'Otro'),
    ]

    expediente = models.ForeignKey(ExpedienteCobranza, on_delete=models.CASCADE, related_name='gestiones')
    tipo_gestion = models.CharField(max_length=25, choices=TIPO_CHOICES)
    resultado = models.CharField(max_length=25, choices=RESULTADO_CHOICES, default='pendiente_respuesta')

    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    notas = models.TextField(blank=True, null=True)

    # Snapshot de lo que se envió (si fue un mensaje), y su estatus real
    # de entrega vía la API del proveedor (Twilio, SMTP, etc.)
    mensaje_enviado = models.TextField(blank=True, null=True)
    envio_exitoso = models.BooleanField(null=True, blank=True)
    envio_id_externo = models.CharField(max_length=100, blank=True, null=True)
    envio_error = models.TextField(blank=True, null=True)

    # Recordatorio de seguimiento -- "la próxima acción"
    proxima_accion_fecha = models.DateField(null=True, blank=True)
    proxima_accion_descripcion = models.CharField(max_length=255, blank=True, null=True)
    proxima_accion_completada = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha']  # noqa: RUF012

    def __str__(self):
        return f"{self.get_tipo_gestion_display()} — {self.expediente.cliente.nombre} — {self.fecha:%d/%m/%Y}"


# ============================================================
# 3. Plantillas de mensajes/cartas -- reutilizables, con placeholders
# ============================================================

class PlantillaCobranza(models.Model):
    CANAL_CHOICES = [  # noqa: RUF012
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Correo electrónico'),
        ('carta_extrajudicial', 'Carta extrajudicial (PDF)'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='plantillas_cobranza')
    canal = models.CharField(max_length=25, choices=CANAL_CHOICES)
    nombre = models.CharField(max_length=100, help_text="Nombre interno para identificarla, ej. 'Recordatorio 5 días'.")
    etapa_sugerida = models.CharField(
        max_length=25, choices=ExpedienteCobranza.ETAPA_CHOICES, blank=True, null=True,
        help_text="En qué etapa del pipeline se sugiere usar esta plantilla (opcional)."
    )
    asunto = models.CharField(max_length=200, blank=True, null=True, help_text="Solo aplica para correo.")
    cuerpo = models.TextField(
        help_text="Usa placeholders: {nombre_cliente}, {monto_vencido}, {dias_atraso}, "
                   "{folios_pendientes}, {propiedades},{nombre_empresa}, {fecha_hoy}."
    )
    activa = models.BooleanField(default=True)

     # NUEVO -- solo se usan cuando canal="whatsapp" y quieres mandar por
    # una plantilla ya aprobada en Twilio (Content Template), en vez de
    # texto libre. Si content_sid esta vacio, WhatsApp sigue mandando
    # "cuerpo" como texto libre, exactamente igual que hasta ahora.
    content_sid = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Solo para WhatsApp -- el Content SID (empieza con HX) de tu plantilla ya aprobada en Twilio."
    )
    orden_variables = models.CharField(
        max_length=300, blank=True, null=True,
        help_text=(
            "Solo para WhatsApp con content_sid -- lista los placeholders en el orden exacto "
            "en que aparecen en tu plantilla de Twilio, separados por coma. Ej: nombre_cliente,monto_vencido,dias_atraso "
            "-- el primero se manda como variable 1, el segundo como variable 2, etc."
        )
    )

    class Meta:
        ordering = ['canal', 'nombre']  # noqa: RUF012


    def __str__(self):
        return f"{self.get_canal_display()} — {self.nombre}"


    def _construir_contexto(self, expediente):
        """Arma el diccionario de valores reales del expediente -- se
        reutiliza tanto para texto libre (renderizar) como para
        Content Templates de WhatsApp (renderizar_content_variables)."""
        facturas = expediente._facturas_vencidas_lista
        folios = ", ".join(f.folio for f in facturas) or "N/D"
 
        propiedades_vistas = []
        for f in facturas:
            identificador = self._identificador_propiedad(f)
            if identificador not in propiedades_vistas:
                propiedades_vistas.append(identificador)
        propiedades = ", ".join(propiedades_vistas) or "N/D"
 
        return {
            "nombre_cliente": expediente.cliente.nombre,
            "monto_vencido": f"${expediente.saldo_vencido_total:,.2f}",
            "dias_atraso": str(expediente.dias_atraso_maximo),
            "folios_pendientes": folios,
            "propiedades": propiedades,
            "nombre_empresa": expediente.empresa.nombre,
            "fecha_hoy": self._hoy_formateada(),
        }

    def renderizar(self, expediente):
        """Sustituye los placeholders con los datos reales del expediente
        -- para texto libre (correo, SMS, carta, o WhatsApp sin content_sid)."""
        contexto = self._construir_contexto(expediente)
        cuerpo = self.cuerpo
        asunto = self.asunto or ""
        for clave, valor in contexto.items():
            cuerpo = cuerpo.replace("{" + clave + "}", valor)
            asunto = asunto.replace("{" + clave + "}", valor)
        return asunto, cuerpo
 
    def renderizar_content_variables(self, expediente):
        """Arma el JSON de content_variables que pide Twilio para un
        Content Template de WhatsApp, ej: '{"1":"Ana Rocha","2":"$7,000.00"}'.
        Usa el orden definido en 'orden_variables'. Regresa None si esta
        plantilla no tiene content_sid configurado."""
        from json import dumps as _json_dumps  # import local -- evita el
        # conflicto con cualquier otro "json" ya importado en este archivo

        if not self.content_sid or not self.orden_variables:
            return None

        contexto = self._construir_contexto(expediente)
        # NUEVO -- acepta el nombre con o sin llaves ({fecha_hoy} o
        # fecha_hoy), para que no importe cómo lo hayas capturado.
        claves_en_orden = [
            c.strip().lstrip("{").rstrip("}").strip()
            for c in self.orden_variables.split(",")
            if c.strip()
        ]

        variables = {}
        for i, clave in enumerate(claves_en_orden, start=1):
            variables[str(i)] = contexto.get(clave, "")

        return _json_dumps(variables, ensure_ascii=False)
 
    @staticmethod
    def _identificador_propiedad(factura):
        """Regresa 'Local {numero}' o 'Área {nombre}' según de dónde
        venga la factura -- ajusta los nombres de campo (numero/nombre)
        si en tu modelo real se llaman distinto."""
        if getattr(factura, "local_id", None) and factura.local:
            return f"Local {factura.local.numero}"
        if getattr(factura, "area_comun_id", None) and factura.area_comun:
            return f"Área {factura.area_comun.nombre}"
        return "N/D"
    
    @staticmethod
    def _hoy_formateada():
        return timezone.now().strftime("%d de %B de %Y")


# ============================================================
# 4. Plan de Pago -- acuerdo formal con el deudor
# ============================================================

class PlanDePago(models.Model):
    ESTATUS_CHOICES = [  # noqa: RUF012
        ('activo', 'Activo'),
        ('cumplido', 'Cumplido'),
        ('incumplido', 'Incumplido'),
        ('cancelado', 'Cancelado'),
    ]

    expediente = models.ForeignKey(ExpedienteCobranza, on_delete=models.CASCADE, related_name='planes_pago')
    fecha_acuerdo = models.DateField(auto_now_add=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    numero_parcialidades = models.PositiveIntegerField()
    estatus = models.CharField(max_length=15, choices=ESTATUS_CHOICES, default='activo')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notas = models.TextField(blank=True, null=True)
    comprobante_acuerdo = models.FileField(upload_to='cobranza/planes_pago/', blank=True, null=True)

    class Meta:
        ordering = ['-fecha_acuerdo']  # noqa: RUF012

    def __str__(self):
        return f"Plan de pago — {self.expediente.cliente.nombre} — {self.numero_parcialidades} parcialidades"

    def actualizar_estatus(self):
        parcialidades = self.parcialidades.all()
        if all(p.estatus == 'pagada' for p in parcialidades):
            self.estatus = 'cumplido'
        elif any(p.estatus == 'vencida' for p in parcialidades):
            self.estatus = 'incumplido'
        self.save(update_fields=['estatus'])


class ParcialidadPlanPago(models.Model):
    ESTATUS_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
    ]

    plan = models.ForeignKey(PlanDePago, on_delete=models.CASCADE, related_name='parcialidades')
    numero = models.PositiveIntegerField()
    fecha_vencimiento = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estatus = models.CharField(max_length=15, choices=ESTATUS_CHOICES, default='pendiente')
    fecha_pago = models.DateField(null=True, blank=True)
    pago = models.ForeignKey('facturacion.Pago', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['plan', 'numero']  # noqa: RUF012
        unique_together = ('plan', 'numero')

    def __str__(self):
        return f"Parcialidad {self.numero}/{self.plan.numero_parcialidades} — ${self.monto}"