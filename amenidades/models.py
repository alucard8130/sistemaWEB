from django.db import models
from django.conf import settings
from empresas.models import Empresa    


class Amenidad(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='amenidades')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    capacidad_maxima = models.PositiveIntegerField(null=True, blank=True)
    hora_apertura = models.TimeField(default='08:00')
    hora_cierre = models.TimeField(default='22:00')
    duracion_maxima_horas = models.PositiveIntegerField(default=4)
    costo_reservacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    requiere_deposito = models.BooleanField(default=False)
    monto_deposito = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dias_anticipacion_minima = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('empresa', 'nombre')

    def __str__(self):
        return self.nombre


class Reservacion(models.Model):
    ESTADO_CHOICES = [
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    amenidad = models.ForeignKey(Amenidad, on_delete=models.PROTECT, related_name='reservaciones')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE)
    propiedad = models.ForeignKey('locales.LocalComercial', on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    numero_invitados = models.PositiveIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='confirmada')
    factura_generada = models.ForeignKey(
        'facturacion.FacturaOtrosIngresos', on_delete=models.SET_NULL, null=True, blank=True
    )
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cancelado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservaciones_canceladas')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    observaciones = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['fecha', 'hora_inicio']