from django.conf import settings
from django.db import models


class IngresoEscuela(models.Model):
    """Ingresos importados desde un Excel externo (ej. Academic+ Control)
    -- ligeros, sin cliente ni factura, solo para alimentar graficos y
    comparativos de Tesoreria/Presupuestos en el mini ERP de escuelas."""

    CATEGORIA_CHOICES = [  # noqa: RUF012
        ('colegiatura', 'Colegiatura'),
        ('inscripcion', 'Inscripción'),
        ('otro', 'Otro'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='ingresos_escuela')
    fecha = models.DateField()
    concepto = models.CharField(max_length=255)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro')
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    fecha_importacion = models.DateTimeField(auto_now_add=True)
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    archivo_origen = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Nombre del archivo Excel del que se importó, para rastrear el origen."
    )

    class Meta:
        ordering = ['-fecha']  # noqa: RUF012

    def __str__(self):
        return f"{self.fecha} -- {self.concepto}: ${self.monto}"
