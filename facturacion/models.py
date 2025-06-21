
# Create your models here.
from django.db import models
from django.conf import settings
from empresas.models import Empresa
from clientes.models import Cliente
from locales.models import LocalComercial
from areas.models import AreaComun

class Factura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    local = models.ForeignKey(LocalComercial, on_delete=models.SET_NULL, null=True, blank=True)
    area_comun = models.ForeignKey(AreaComun, on_delete=models.SET_NULL, null=True, blank=True)
    TIPO_CUOTA_CHOICES = [
        ('mantenimiento', 'Mantenimiento'),
        ('renta', 'Renta'),
        ('deposito garantia', 'Deposito Garantía'),
        ('servicios', 'Servicios'),
        ('extraordinaria', 'Extraordinaria'),
        ('penalidad', 'Penalidad'),
        ('publicidad', 'Publicidad'),
    ]   
    tipo_cuota= models.CharField(max_length=100, choices=TIPO_CUOTA_CHOICES)
    folio = models.CharField(max_length=100, unique=True)
    cfdi = models.FileField(upload_to='fact_sat/', max_length=255, blank=True, null=True)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    monto = models.DecimalField(max_digits=20, decimal_places=2)
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    estatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    observaciones = models.CharField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"
    
    class Meta:
        ordering = ['-fecha_emision']
    
  
    @property
    def total_pagado(self):
        return sum(pago.monto for pago in self.pagos.all())

    @property
    def saldo_pendiente(self):
        if  self.estatus == 'cancelada':
            return 0
        if self.estatus == 'pagada' or 'pendiente':
            return self.monto - self.total_pagado
    
    def actualizar_estatus(self):
        if self.saldo_pendiente <= 0:
            self.estatus = 'pagada'
        else:
            self.estatus = 'pendiente'
        self.save()

class Pago(models.Model):
    FORMAS_PAGO = [
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('nota_credito', 'Nota de Crédito'),
        ('deposito', 'Depósito'),
        ('efectivo', 'Efectivo'),
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
    
    

    
         