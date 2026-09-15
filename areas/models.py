
from django import forms
from django.db import models
from django.utils import timezone

from catalogos.utils import generar_referencia_pago_propiedad
from empresas.models import Empresa


# Create your models here.
class AreaComun(models.Model):
    numero = models.CharField(max_length=100)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, null=True, blank=True) 
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    TIPO_AREA_CHOICES = [  # noqa: RUF012
        ('Modulo', 'modulo'),
        ('Stand', 'stand'),
        ('Espacio', 'superficie'),
        ('Isla', 'isla'),
        ('Cajon', 'cajon'),
        ('Area', 'area'),
        ('Otro', 'otro'),
        ]
    tipo_area = models.CharField(max_length=20, choices=TIPO_AREA_CHOICES, default='Modulo')
    cantidad_areas = models.PositiveIntegerField(default=1, blank=True, null=True)
    cuota = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    deposito = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    giro = models.CharField(max_length=100, blank=True, null=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True)
    STATUS_CHOICES = [  # noqa: RUF012
        ('ocupado', 'Ocupado'),
        ('disponible', 'Disponible'),
        ('mantenimiento', 'Mantenimiento'),
        ('en_juicio', 'En juicio'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponible')
    fecha_inicial = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    es_cuota_anual = models.BooleanField(default=False, verbose_name="¿Cuota global? un solo pago")
    referencia_pago = models.CharField(max_length=32, unique=True, blank=True, null=True)
    es_cuota_variable = models.BooleanField(
        default=False,
        verbose_name="¿Cuota variable?",
        help_text="Si está activo, el importe NO se captura aquí -- se determina "
                   "cada vez que el usuario factura manualmente esta área. Esta "
                   "área nunca se incluye en la facturación mensual automática."
    )
    PERIODICIDAD_CHOICES = [  # noqa: RUF012
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]
    periodicidad_facturacion = models.CharField(
        max_length=20, choices=PERIODICIDAD_CHOICES, default='mensual',
        help_text="Se sincroniza automáticamente desde el contrato vigente -- "
                   "determina cada cuánto se factura esta área."
    )
   


    def save(self, *args, **kwargs):
        if not self.referencia_pago and self.cliente_id:
            nueva_ref = generar_referencia_pago_propiedad(self.cliente_id, 'A', self.numero)
            intentos = 0
            while AreaComun.objects.filter(referencia_pago=nueva_ref).exists() and intentos < 5:
                nueva_ref = generar_referencia_pago_propiedad(self.cliente_id, 'A', self.numero)
                intentos += 1
            self.referencia_pago = nueva_ref
        super().save(*args, **kwargs)


    @property
    def estado_contrato_actual(self):
        """Estatus real del contrato vigente/vencido_ocupado de esta
        area -- reemplaza el criterio antiguo basado solo en fecha_fin
        (que se volvia obsoleto en cuanto el contrato se extendia mes
        a mes via el comando de renovacion automatica)."""
        contrato = self.contratos.filter(estatus__in=['vigente', 'vencido_ocupado']).first()
        return contrato.estatus if contrato else None

        
    @property
    def estado_vigencia(self):
        if self.fecha_fin and self.fecha_fin < timezone.now().date():
            return "Vencido"
        return "Vigente"

    widgets = {  # noqa: RUF012
            'fecha_inicial': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __str__(self):
        return f"{self.numero}"

    class Meta:
        unique_together = ('empresa', 'numero')


