from django.db import models
from django.contrib.auth.models import User
from empresas.models import Empresa,CuentaBancaria



class TraspasoBancario(models.Model):
    ESTADO_CHOICES = [
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name='traspasos'
    )
    cuenta_origen = models.ForeignKey(
        CuentaBancaria, on_delete=models.PROTECT,
        related_name='traspasos_salida'
    )
    cuenta_destino = models.ForeignKey(
        CuentaBancaria, on_delete=models.PROTECT,
        related_name='traspasos_entrada'
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()
    concepto = models.CharField(max_length=255, blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='completado')
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    # NUEVO — solo para trazabilidad/reporte de inversión
    es_inversion = models.BooleanField(default=False)
    retencion_isr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gasto_generado = models.ForeignKey(
        'gastos.Gasto', on_delete=models.SET_NULL, null=True, blank=True  # ajusta la app real
    )
    # NUEVO
    TIPO_MOVIMIENTO_INVERSION_CHOICES = [
        ('incremento', 'Incremento de inversión'),
        ('retiro', 'Retiro / Liquidación de inversión'),
    ]
    tipo_movimiento_inversion = models.CharField(
        max_length=30, choices=TIPO_MOVIMIENTO_INVERSION_CHOICES, blank=True, null=True
    )

    def __str__(self):
        return f"Traspaso {self.fecha} — ${self.monto} de {self.cuenta_origen} a {self.cuenta_destino}"

    class Meta:
        verbose_name = 'Traspaso bancario'
        verbose_name_plural = 'Traspasos bancarios'
        ordering = ['-fecha', '-fecha_registro']

