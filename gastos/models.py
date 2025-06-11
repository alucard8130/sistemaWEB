
# Create your models here.
from django.db import models
from empleados.models import Empleado
from empresas.models import Empresa
from proveedores.models import Proveedor


class GrupoGasto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class SubgrupoGasto(models.Model):
    grupo = models.ForeignKey('GrupoGasto', on_delete=models.CASCADE, related_name='subgrupos')
    nombre = models.CharField(max_length=100)

    class Meta:
        unique_together = ('grupo', 'nombre')
        verbose_name = "Subgrupo de Gasto"
        verbose_name_plural = "Subgrupos de Gasto"

    def __str__(self):
        return f"{self.grupo} / {self.nombre}"

class TipoGasto(models.Model):
    subgrupo = models.ForeignKey(SubgrupoGasto, on_delete=models.CASCADE, related_name='tipos')
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.subgrupo} - {self.nombre}"

class Gasto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_gasto = models.ForeignKey(TipoGasto, on_delete=models.PROTECT)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    comprobante = models.FileField(upload_to='comprobantes/', blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.fecha} - {self.tipo_gasto} - ${self.monto}"    