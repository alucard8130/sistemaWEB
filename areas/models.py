
from django import forms
from django.db import models
from clientes.models import Cliente
from empresas.models import Empresa

# Create your models here.
class AreaComun(models.Model):
    #num_contrato = models.AutoField(primary_key=True)
    numero = models.CharField(max_length=100)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, null=True, blank=True) 
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cuota = models.DecimalField(max_digits=10, decimal_places=2)
    giro = models.CharField(max_length=100, blank=True, null=True)
    ubicacion = models.CharField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    STATUS_CHOICES = [
        ('ocupado', 'Ocupado'),
        ('disponible', 'Disponible'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ocupado')
    fecha_inicial = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    observaciones = models.CharField(blank=True, null=True)

    widgets = {
            'fecha_inicial': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __str__(self):
        return f"{self.numero} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'numero')
