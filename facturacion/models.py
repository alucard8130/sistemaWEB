
# Create your models here.
from django.db import models
from django.conf import settings
from empresas.models import Empresa
from clientes.models import Cliente
from locales.models import LocalComercial
from areas.models import AreaComun
from django.db.models import Sum

class Factura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    local = models.ForeignKey(LocalComercial, on_delete=models.SET_NULL, null=True, blank=True)
    area_comun = models.ForeignKey(AreaComun, on_delete=models.SET_NULL, null=True, blank=True)
    TIPO_CUOTA_CHOICES = [
        ('mantenimiento', 'Mantenimiento'),
        ('renta', 'Renta'),
        ('deposito', 'Deposito Garantía'),
        ('extraordinaria', 'Extraordinaria'),
        ('penalidad', 'Multa'),
        ('intereses', 'Intereses'),
    ]   
    tipo_cuota= models.CharField(max_length=100, choices=TIPO_CUOTA_CHOICES)
    folio = models.CharField(max_length=100)
    uuid= models.CharField(max_length=100, blank=True, null=True)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    monto = models.DecimalField(max_digits=20, decimal_places=2)
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('cobrada', 'Cobrada'),
        ('cancelada', 'Cancelada'),
    ]
    estatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    observaciones = models.CharField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    facturama_id = models.CharField(max_length=100, blank=True, null=True)  
    
    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"
    
    class Meta:
        ordering = ['-fecha_emision']
        unique_together = ('folio', 'empresa')  # Folio único por empresa
    
  
    @property
    def total_pagado(self):
        return sum(pago.monto for pago in self.pagos.all())
    
    @property
    def saldo_pendiente(self):
        if self.estatus == 'cancelada':
            return 0
        if self.estatus in ('cobrada', 'pendiente'):
            return float(self.monto) - float(self.total_pagado)
        return 0
  

    def actualizar_estatus(self):
        total_pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
       
        if total_pagado >= self.monto:
            self.estatus = 'cobrada'
        elif total_pagado == 0:
            self.estatus = 'pendiente'
        else:
            self.estatus = 'pendiente'  # O podrías poner un "parcial" si agregas esa opción
        self.save()

class Pago(models.Model):
    FORMAS_PAGO = [
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('nota_credito', 'Nota de Crédito'),
        ('deposito', 'Depósito'),
        ('efectivo', 'Efectivo'),
        ('stripe', 'Stripe'),
        ('otro', 'Otro'),
    ]
    factura = models.ForeignKey('Factura', on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField(blank=True, null=True)
    monto = models.DecimalField(max_digits=20, decimal_places=2)
    forma_pago = models.CharField(max_length=100, choices=FORMAS_PAGO, default='transferencia')
    comprobante = models.FileField(upload_to='comprobantes/', blank=True, null=True)
    registrado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Pago de ${self.monto} a {self.factura.folio} el {self.fecha_pago}"
    

 #modulo otros ingresos   
class FacturaOtrosIngresos(models.Model):
    empresa= models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    tipo_ingreso = models.ForeignKey('TipoOtroIngreso', on_delete=models.PROTECT)
    folio = models.CharField(max_length=50, unique=True)
    uuid= models.CharField(max_length=100, blank=True, null=True)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estatus = models.CharField(max_length=20, choices=[('pendiente','Pendiente'),('cobrada','Cobrada'),('cancelada','Cancelada')], default='pendiente')
    observaciones = models.CharField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    facturama_id = models.CharField(max_length=100, blank=True, null=True)  # Nuevo campo para almacenar el ID de Facturama

    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"
    
    # @property
    # def saldo(self):
    #     total_cobrado = sum(c.monto for c in self.cobros.all())
    #     return float(self.monto) - float(total_cobrado)     
    
    @property
    def saldo(self):
        if self.estatus == 'cancelada':
            return 0
        if self.estatus in ('cobrada', 'pendiente'):
            #total_cobrado = sum(c.monto for c in self.cobros.all())
            return float(self.monto) - float(self.total_cobrado)
        return 0

    @property
    def total_cobrado(self):
        return sum(c.monto for c in self.cobros.all())
    
    def actualizar_estatus(self):
        total_cobrado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0

        if total_cobrado >= self.monto:
            self.estatus = 'cobrada'
        elif total_cobrado == 0:
            self.estatus = 'pendiente'
        else:
            self.estatus = 'pendiente'  # O podrías poner un "parcial" si agregas esa opción
        self.save()

class CobroOtrosIngresos(models.Model):
    FORMAS_PAGO = [
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('nota_credito', 'Nota de Crédito'),
        ('deposito', 'Depósito'),
        ('efectivo', 'Efectivo'),
        ('otro', 'Otro'),
    ]
    factura = models.ForeignKey(FacturaOtrosIngresos, on_delete=models.CASCADE, related_name='cobros')
    fecha_cobro = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    forma_cobro = models.CharField(max_length=20, choices=FORMAS_PAGO, default='transferencia')
    comprobante = models.FileField(upload_to='comprobantes_oi/', blank=True, null=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Cobro de ${self.monto} para {self.factura.folio} el {self.fecha_cobro}"
    
class TipoOtroIngreso(models.Model):
    nombre = models.CharField(max_length=100)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
    
