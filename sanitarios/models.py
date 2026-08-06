import random
import string
from django.conf import settings
from django.db import models
from empresas.models import Empresa  # ajusta el import real
import uuid


class CasetaOperador(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='casetas_sanitario')
    nombre = models.CharField(max_length=100, help_text="Ej. 'Caseta Principal', 'Estacionamiento Sur'")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

    
class UsoSanitario(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de cobro'),
        ('cobrado', 'Cobrado'),
        ('cancelado', 'Cancelado'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usos_sanitario')
    codigo = models.CharField(max_length=10, db_index=True)  # antes: max_length=6
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    monto = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    fecha_generado = models.DateTimeField(auto_now_add=True)
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    fecha_cobro = models.DateTimeField(null=True, blank=True)
    cobrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    caseta = models.ForeignKey(
        CasetaOperador, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='usos',
        help_text="Si el uso se registró desde una caseta compartida (sin login), queda aquí en vez de en generado_por/cobrado_por."
    )

    def __str__(self):
        return f"{self.codigo} — {self.get_estado_display()}"

    class Meta:
        ordering = ['-fecha_generado']

    @staticmethod   
    def generar_codigo_unico(empresa):
        for _ in range(20):
            codigo = ''.join(random.choices(string.digits, k=4))
            if not UsoSanitario.objects.filter(empresa=empresa, codigo=codigo, estado='pendiente').exists():
                return codigo
        raise Exception("No se pudo generar un código único, intenta de nuevo.")


class CorteSanitario(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cortes_sanitario')
    fecha = models.DateField()
    total_cobrado = models.DecimalField(max_digits=10, decimal_places=2)
    factura = models.ForeignKey('facturacion.FacturaOtrosIngresos', on_delete=models.SET_NULL, null=True, blank=True)
    cerrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fecha_cierre = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'fecha')  # nunca se puede cerrar el mismo día dos veces

    def __str__(self):
        return f"Corte {self.fecha} — {self.empresa.nombre}"



class BoletoFisico(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('usado', 'Usado'),
        ('cancelado', 'Cancelado'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='boletos_fisicos')
    codigo = models.CharField(max_length=10)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    uso = models.OneToOneField(UsoSanitario, on_delete=models.SET_NULL, null=True, blank=True, related_name='boleto_consumido')

    cargado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'codigo')  # no se puede cargar el mismo folio dos veces
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} — {self.get_estado_display()}"