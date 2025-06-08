
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
    observaciones = models.CharField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-fecha_emision']
    
    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"

  
    @property
    def total_pagado(self):
        return sum(pago.monto for pago in self.pagos.all())

    @property
    def saldo_pendiente(self):
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
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pago = models.CharField(max_length=20, choices=FORMAS_PAGO, default='transferencia')
    registrado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Pago de ${self.monto} a {self.factura.folio} el {self.fecha_pago}"
    
    

    
         