from django.db import models

from empresas.models import CuentaBancaria, Empresa

# Create your models here.
class CorteEstacionamiento(models.Model):
    PERIODO_CHOICES = [
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=20, choices=PERIODO_CHOICES, default='mensual')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    total_efectivo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tarjeta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_boletos = models.PositiveIntegerField(default=0)

    # Liquidación al operador
    tiene_operador_externo = models.BooleanField(default=False)
    nombre_operador = models.CharField(max_length=100, blank=True, null=True)
    porcentaje_operador = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text="% que corresponde al operador. 0 si es 100% de la plaza.")
    monto_renta_operador = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text="Renta fija que paga el operador, si aplica.")

    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.PROTECT, null=True, blank=True,related_name='cortes_estacionamiento')
    # Factura generada para este corte
    factura = models.OneToOneField(
        'facturacion.FacturaOtrosIngresos',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='corte_estacionamiento'
    )
    observaciones = models.TextField(blank=True, null=True)
    archivo_origen = models.FileField(upload_to='estacionamiento/', blank=True, null=True)
    registrado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_deposito = models.DateField(null=True, blank=True, verbose_name="Fecha de depósito en banco")

    @property
    def total_ingresos_brutos(self):
        return self.total_efectivo + self.total_tarjeta

    @property
    def monto_operador(self):
        """Lo que le corresponde al operador externo"""
        if not self.tiene_operador_externo:
            return 0
        por_porcentaje = self.total_ingresos_brutos * (self.porcentaje_operador / 100)
        return por_porcentaje + self.monto_renta_operador

    @property
    def ingreso_neto_plaza(self):
        """Lo que queda para la plaza después de pagar al operador"""
        return self.total_ingresos_brutos - self.monto_operador

    @property
    def label_periodo(self):
        if self.periodo == 'semanal':
            return f"Semana {self.fecha_inicio.strftime('%d/%m/%Y')} al {self.fecha_fin.strftime('%d/%m/%Y')}"
        elif self.periodo == 'quincenal':
            return f"Quincena {self.fecha_inicio.strftime('%d/%m/%Y')} al {self.fecha_fin.strftime('%d/%m/%Y')}"
        else:
            return f"Mes {self.fecha_inicio.strftime('%B %Y').capitalize()}"

    def __str__(self):
        return f"{self.label_periodo} — ${self.ingreso_neto_plaza}"

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Corte de estacionamiento'
        verbose_name_plural = 'Cortes de estacionamiento'


class TicketEstacionamiento(models.Model):
    corte = models.ForeignKey(CorteEstacionamiento, on_delete=models.CASCADE, related_name='tickets')
    numero_ticket = models.CharField(max_length=50)
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    minutos = models.PositiveIntegerField(default=0)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    FORMA_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
    ]
    forma_pago = models.CharField(max_length=20, choices=FORMA_PAGO_CHOICES)

    def __str__(self):
        return f"Ticket {self.numero_ticket} — ${self.monto}"

    class Meta:
        ordering = ['fecha', 'hora_salida']