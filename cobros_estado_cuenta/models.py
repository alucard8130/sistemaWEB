
# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from empresas.models import Empresa, CuentaBancaria


class SesionEstadoCuenta(models.Model):
    """Representa una sesión de procesamiento de un estado de cuenta bancario"""
    ESTADO_CHOICES = [
        ('procesando', 'Procesando'),
        ('listo', 'Listo para revisar'),
        ('aplicado', 'Aplicado'),
        ('error', 'Error'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sesiones_estado_cuenta')
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.PROTECT, null=True, blank=True)
    archivo = models.FileField(upload_to='estados_cuenta_pdf/')
    banco_detectado = models.CharField(max_length=50, blank=True)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    saldo_inicial = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    saldo_final = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    total_abonos = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='procesando')
    error_detalle = models.TextField(blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.banco_detectado} {self.periodo_inicio} al {self.periodo_fin}"

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Sesión de estado de cuenta'
        verbose_name_plural = 'Sesiones de estado de cuenta'


class MovimientoEstadoCuenta(models.Model):
    """Cada abono extraído del estado de cuenta por Claude"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de asignar'),
        ('asignado_factura', 'Asignado a factura existente'),
        ('factura_nueva', 'Factura nueva creada'),
        ('ignorado', 'Ignorado'),
    ]
    sesion = models.ForeignKey(SesionEstadoCuenta, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateField()
    descripcion = models.TextField()
    referencia = models.CharField(max_length=255, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    # NUEVO: cuánto del monto ya se ha repartido entre facturas
    monto_aplicado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # NUEVO: una vez que se aplica la primera parte, el resto del saldo solo
    # puede seguir asignándose a facturas de este mismo cliente
    cliente_asignado = models.ForeignKey(
        'clientes.Cliente', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_asignados_edc'
    )

    # Matching con cliente
    cliente_detectado = models.ForeignKey(
        'clientes.Cliente', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_estado_cuenta'
    )
    # NUEVO: propiedad detectada por la IA
    propiedad_tipo = models.CharField(
        max_length=10,
        choices=[('local', 'Local Comercial'), ('area', 'Área Común')],
        blank=True, null=True
    )
    propiedad_local = models.ForeignKey(
        'locales.LocalComercial', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_estado_cuenta'
    )
    propiedad_area = models.ForeignKey(
        'areas.AreaComun', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_estado_cuenta'
    )
    
    confianza_match = models.CharField(
        max_length=20,
        choices=[('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja'), ('ninguna', 'Sin match')],
        default='ninguna'
    )
    razon_match = models.CharField(max_length=255, blank=True)
    # Decisión del usuario
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    # Resultado
    pago_generado = models.ForeignKey(
        'facturacion.Pago', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimiento_estado_cuenta'
    )
    factura_otros_ingresos = models.ForeignKey(
        'facturacion.FacturaOtrosIngresos', on_delete=models.SET_NULL,
        null=True, blank=True
    )

    @property
    def saldo_restante(self):
        return self.monto - self.monto_aplicado
    
    class Meta:
        ordering = ['fecha', 'monto']

    def __str__(self):
        return f"{self.fecha} ${self.monto} — {self.descripcion[:50]}"


class AplicacionMovimientoEstadoCuenta(models.Model):
    """Cada parte de un movimiento que se fue repartiendo entre distintas facturas."""
    movimiento = models.ForeignKey(MovimientoEstadoCuenta, on_delete=models.CASCADE, related_name='aplicaciones')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    pago = models.ForeignKey('facturacion.Pago', on_delete=models.SET_NULL, null=True, blank=True)
    cobro_otros_ingresos = models.ForeignKey('facturacion.CobroOtrosIngresos', on_delete=models.SET_NULL, null=True, blank=True)
    factura_cuota = models.ForeignKey('facturacion.Factura', on_delete=models.SET_NULL, null=True, blank=True)
    factura_otros = models.ForeignKey('facturacion.FacturaOtrosIngresos', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_aplicacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_aplicacion']

    def __str__(self):
        return f"{self.movimiento_id} — ${self.monto}"