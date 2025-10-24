
# Create your models here.
from django.db import models
from empresas.models import Empresa

class Empleado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rfc= models.CharField(max_length=13)
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
    

#modulo inicidencias
class Incidencia(models.Model):
    TIPO_CHOICES = [
        ('falta', 'Falta'),
        ('retardo', 'Retardo'),
        ('extra', 'Hora Extra'),
        ('permiso', 'Permiso'),
        ('vacaciones', 'Vacaciones'),
        ('incapacidad', 'Incapacidad'),
        ('dias festivos', 'Festivos trabajados'),
        ('descanso', 'Descansos trabajados'),
        ('descuento', 'Descuento'),
        ('devolucion', 'Devolución'),
        ('otro', 'Otro'),
    ]
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha = models.DateField(help_text="Fecha de la incidencia (o inicio del periodo)")
    fecha_fin = models.DateField(blank=True, null=True, help_text="Solo si aplica periodo (vacaciones, incapacidad, etc.)")
    dias = models.PositiveIntegerField(default=1, help_text="Cantidad de días de la incidencia")
    descripcion = models.TextField(blank=True)
    numero_incapacidad_imss = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="Número de incapacidad IMSS",help_text="Capturar solo si el tipo de incidencia es 'Incapacidad'"
    )
    importe= models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Solo si aplica descuento o devolución",
    )

    def __str__(self):
        if self.fecha_fin:
            return f"{self.empleado.nombre} - {self.get_tipo_display()} ({self.fecha} a {self.fecha_fin})"
        return f"{self.empleado.nombre} - {self.get_tipo_display()} ({self.fecha})"  

 