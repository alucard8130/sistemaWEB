
from django.db import models
#from clientes.models import Cliente
from empresas.models import Empresa

# Create your models here.
class LocalComercial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    propietario = models.CharField(max_length=255)  # Propietario del local
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT,null=True,blank=True) 
    numero = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cuota = models.DecimalField(max_digits=100, decimal_places=2)
    giro = models.CharField(max_length=255, blank=True, null=True)
    STATUS_CHOICES = [
        ('ocupado', 'Ocupado'),
        ('disponible', 'Disponible'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ocupado')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    observaciones = models.CharField(blank=True, null=True)
    es_cuota_anual = models.BooleanField(default=False, verbose_name="¿Cuota anual?")
    
    TIPO_CHOICES = [
        ('local', 'Local Comercial'),
        ('casa', 'Casa'),
        ('departamento', 'Departamento'),
        ('oficina', 'Oficina'),
        ('bodega', 'Bodega'),
        ('terreno', 'Terreno'),
    ]
    tipo_propiedad = models.CharField(max_length=20, choices=TIPO_CHOICES)
    referencia_pago = models.CharField(max_length=32, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.referencia_pago and self.cliente_id:
            from clientes.utils import generar_referencia_pago_propiedad
            nueva_ref = generar_referencia_pago_propiedad(self.cliente_id, 'L', self.numero)
            intentos = 0
            while LocalComercial.objects.filter(referencia_pago=nueva_ref).exists() and intentos < 5:
                nueva_ref = generar_referencia_pago_propiedad(self.cliente_id, 'L', self.numero)
                intentos += 1
            self.referencia_pago = nueva_ref
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero}"
        #return f"{self.numero} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'numero')  # 👈 Unicidad compuesta