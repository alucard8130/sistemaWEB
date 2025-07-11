
# Create your models here.
from django.db import models
from django.db.models import Sum
from empleados.models import Empleado
from empresas.models import Empresa
from proveedores.models import Proveedor
from django.conf import settings
from django.contrib.auth.models import User


class GrupoGasto(models.Model):
    #empresa= models.ForeignKey(Empresa,on_delete=models.CASCADE,null=True,blank=True)
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class SubgrupoGasto(models.Model):
    #empresa= models.ForeignKey(Empresa, null=True,blank=True,on_delete=models.CASCADE)
    grupo = models.ForeignKey('GrupoGasto', on_delete=models.CASCADE, related_name='subgrupos')
    nombre = models.CharField(max_length=100)

   # class Meta:
    #    unique_together = ('grupo', 'nombre')
     #   verbose_name = "Subgrupo de Gasto"
      #  verbose_name_plural = "Subgrupos de Gasto"

    def __str__(self):
        return f"{self.grupo.nombre}/{self.nombre}"
        #return f"{self.nombre}"
    
class TipoGasto(models.Model):
    empresa= models.ForeignKey(Empresa, on_delete=models.CASCADE,null=True,blank=True)
    subgrupo = models.ForeignKey(SubgrupoGasto, on_delete=models.CASCADE, related_name='tipos')
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.subgrupo.nombre}/{self.nombre}"
        #return f"{self.nombre}"

class Gasto(models.Model):
    empresa = models.ForeignKey(Empresa,on_delete=models.CASCADE,null=True,blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_gasto = models.ForeignKey(TipoGasto, on_delete=models.PROTECT)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    comprobante = models.FileField(upload_to='cfdi_gastos/', blank=True, null=True)
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    estatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True)
    retencion_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retencion_isr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.fecha} - {self.tipo_gasto} - ${self.monto}"  

    @property
    def total_pagado(self):
        return sum(p.monto for p in self.pagos.all())

    @property
    def saldo_restante(self):
        total_pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
        return self.monto - total_pagado

    
    def actualizar_estatus(self):
        total_pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
        if total_pagado >= self.monto:
            self.estatus = 'pagada'
        elif total_pagado == 0:
            self.estatus = 'pendiente'
        else:
            self.estatus = 'pendiente'  # O podrías poner un "parcial" si agregas esa opción
        self.save()
   
        

from django.db import models
from django.contrib.auth.models import User

class PagoGasto(models.Model):
    gasto = models.ForeignKey('Gasto', on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    forma_pago = models.CharField(
        max_length=30,
        choices=[('transferencia', 'Transferencia'),('efectivo', 'Efectivo') , ('cheque', 'Cheque'), ('tarjeta', 'Tarjeta')],
        default='transferencia'
    )
    referencia = models.CharField(max_length=100, blank=True, null=True)
    comprobante = models.FileField(upload_to='comprobante_gastos/', blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago de ${self.monto} para solicitud {self.gasto.id}'

    
  