
from django import forms
from django.db import models
from empresas.models import Empresa

# Create your models here.
class AreaComun(models.Model):
    num_contrato = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.CharField(max_length=100, blank=True, null=True)
    numero = models.CharField(max_length=100)
    cuota = models.DecimalField(max_digits=10, decimal_places=2)
    ubicacion = models.CharField(blank=True, null=True)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)
    STATUS_CHOICES = [
        ('ocupado', 'Ocupado'),
        ('disponible', 'Disponible'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ocupado')
    #fecha_inicio = models.DateField(blank=True, null=True)
    #fecha_fin = models.DateField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __str__(self):
        return f"{self.numero} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'numero')
