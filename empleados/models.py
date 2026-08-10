
# Create your models here.
import uuid

from django.db import models

from empresas.models import Empresa


class Empleado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rfc= models.CharField(max_length=13)
    PUESTOS_CHOICES = [  # noqa: RUF012
        ('GERENTE', 'Gerente'),
        ('SUPERVISOR', 'Supervisor'),
        ('JEFE', 'Jefe'),
        ('AUX', 'Auxiliar'),
        ('OPERATIVO', 'Operativo'),
        ('OTRO', 'Otro'),
    ]
    puesto = models.CharField(max_length=30, choices=PUESTOS_CHOICES)
    DEPARTAMENTO_CHOICES = [  # noqa: RUF012
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
    token_asistencia = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True,
        help_text="Identifica al empleado en el link de marcar asistencia (sin necesidad de login)."
    )
    hora_entrada_esperada = models.TimeField(
        null=True, blank=True, help_text="Hora esperada de entrada, ej. 08:00"
    )
    hora_salida_esperada = models.TimeField(
        null=True, blank=True, help_text="Hora esperada de salida, ej. 17:00"
    )
    tolerancia_minutos = models.PositiveIntegerField(
        default=10, help_text="Minutos de gracia antes de contar retardo"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    # NUEVO: una vez que el horario se edita (después de la creación), se bloquea
    horario_bloqueado = models.BooleanField(
            default=False,
            help_text="Una vez editado el horario esperado, solo un superusuario puede volver a modificarlo."
        )
    
    def __str__(self):
        #return f"{self.nombre} ({self.empresa.nombre})"
        return f"{self.nombre}"
    
    @property
    def url_marcar_asistencia(self):
        """Ruta relativa del link único para marcar asistencia (sin dominio)."""
        from django.urls import reverse
        return reverse('marcar_asistencia', kwargs={'token': self.token_asistencia})
    

#modulo inicidencias
class Incidencia(models.Model):
    TIPO_CHOICES = [  # noqa: RUF012
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

 
#regitsro de asistencia 
class RegistroAsistencia(models.Model):
    """Registro diario de entrada/salida de un empleado, con geolocalización."""

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='registros_asistencia')
    fecha = models.DateField()

    hora_entrada = models.DateTimeField(null=True, blank=True, help_text="Hora esperada de entrada, ej. 08:00")
    lat_entrada = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng_entrada = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distancia_metros_entrada = models.FloatField(null=True, blank=True)
    dentro_de_rango_entrada = models.BooleanField(null=True, blank=True)

    hora_inicio_comida = models.DateTimeField(null=True, blank=True)
    lat_inicio_comida = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng_inicio_comida = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distancia_metros_inicio_comida = models.FloatField(null=True, blank=True)
    dentro_de_rango_inicio_comida = models.BooleanField(null=True, blank=True)

    hora_fin_comida = models.DateTimeField(null=True, blank=True)
    lat_fin_comida = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng_fin_comida = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distancia_metros_fin_comida = models.FloatField(null=True, blank=True)
    dentro_de_rango_fin_comida = models.BooleanField(null=True, blank=True)

    hora_salida = models.DateTimeField(null=True, blank=True, help_text="Hora esperada de salida, ej. 17:00")
    lat_salida = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng_salida = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distancia_metros_salida = models.FloatField(null=True, blank=True)
    dentro_de_rango_salida = models.BooleanField(null=True, blank=True)

    @property
    def en_comida(self):
        return bool(self.hora_inicio_comida and not self.hora_fin_comida)

    @property
    def minutos_comida(self):
        if self.hora_inicio_comida and self.hora_fin_comida:
            return round((self.hora_fin_comida - self.hora_inicio_comida).total_seconds() / 60)
        return None

    def __str__(self):
        return f"{self.empleado.nombre} - {self.fecha}"

    class Meta:
        verbose_name = 'Registro de Asistencia'
        verbose_name_plural = 'Registros de Asistencia'
        unique_together = ('empleado', 'fecha')  # un registro por empleado por día
        ordering = ['-fecha'] 


class UbicacionEnVivo(models.Model):
    """Última ubicación reportada por el celular del empleado mientras
    tiene el checador (o la app) abierto. No es historial, es solo el
    estado más reciente -- se sobrescribe en cada ping."""
    empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE, related_name='ubicacion_en_vivo_rel')
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distancia_metros = models.FloatField(null=True, blank=True)
    dentro_de_zona = models.BooleanField(null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ubicación de {self.empleado.nombre} — {self.actualizado_en}"