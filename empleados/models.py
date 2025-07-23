
# Create your models here.
from django.db import models
from empresas.models import Empresa

class Empleado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rfc= models.CharField(max_length=13, unique=True)
    PUESTOS_CHOICES = [
        ('GERENTE', 'Gerente'),
        ('SUPERVISOR', 'Supervisor'),
        ('JEFE', 'Jefe'),
        ('AUX', 'Auxiliar'),
        ('OPERATIVO', 'Operativo'),
        ('OTRO', 'Otro'),
    ]
    puesto = models.CharField(max_length=30, choices=PUESTOS_CHOICES)
    DEPARTAMENTO_CHOICES = [
        ('ADMIN', 'Administracion'),
        ('CONTA', 'Contabilidad'),
        ('MANTTO', 'Mantenimiento'),
        ('EST', 'Estacionamiento'),
        ('LIMP', 'Limpieza'),
        ('SEG', 'Seguridad'),
        ('OTRO', 'Otro'),
    ]
    departamento = models.CharField(max_length=30, choices=DEPARTAMENTO_CHOICES)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        #return f"{self.nombre} ({self.empresa.nombre})"
        return f"{self.nombre}"