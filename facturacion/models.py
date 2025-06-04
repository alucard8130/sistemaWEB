
# Create your models here.
from django.db import models
from empresas.models import Empresa
from clientes.models import Cliente
from locales.models import LocalComercial
from areas.models import AreaComun

class Factura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    local = models.ForeignKey(LocalComercial, on_delete=models.SET_NULL, null=True, blank=True)
    area_comun = models.ForeignKey(AreaComun, on_delete=models.SET_NULL, null=True, blank=True)

    folio = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    estatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"

    class Meta:
        ordering = ['-fecha_emision']
