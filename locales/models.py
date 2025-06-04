
from django.db import models
from clientes.models import Cliente
from empresas.models import Empresa

# Create your models here.
class LocalComercial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    #cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    #cliente = models.CharField(max_length=100, null=True, blank=True)  # Cambiado a CharField para evitar problemas de referencia circular
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    numero = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cuota = models.DecimalField(max_digits=100, decimal_places=2)
    STATUS_CHOICES = [
        ('ocupado', 'Ocupado'),
        ('disponible', 'Disponible'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ocupado')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    observaciones = models.CharField(blank=True, null=True)


    def __str__(self):
        return f"{self.numero} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'numero')  # 👈 Unicidad compuesta