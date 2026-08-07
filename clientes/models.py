from django.db import models

from empresas.models import Empresa


class Cliente(models.Model):
    CHOISE_REGIMEN_FISCAL = [  # noqa: RUF012
        ('601', 'General de Ley Personas Morales'),
        ('603', 'Personas Morales con Fines no Lucrativos'),
        ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
        ('606', 'Arrendamiento'),
        ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
        ('616', 'Sin obligaciones fiscales'),
        ('621', 'Incorporación Fiscal'),
        ('626', 'Régimen Simplificado de Confianza'),
    ]
    CHOISE_USO_CFDI = [  # noqa: RUF012
        ('G03', 'Gastos en general'),
        ('S01', 'Sin efectos fiscales'),
    ]
    CHOISE_TIPO_CONTRIBUYENTE = [  # noqa: RUF012
        ('Fisica', 'Persona Física'),
        ('Moral', 'Persona Moral'),
        ('Publico general', 'Público en General'),
    ]
    CHOISE_OBJETO_IMPUESTO = [  # noqa: RUF012
        ('01', 'No objeto de impuesto'),
        ('02', 'Sí objeto de impuesto'),
        ('03', 'Sí objeto de impuesto y no obligado al desglose'),
    ]

    id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rfc = models.CharField(max_length=13, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    regimen_fiscal = models.CharField(max_length=100, choices=CHOISE_REGIMEN_FISCAL, blank=True, null=True)
    uso_cfdi = models.CharField(max_length=100, choices=CHOISE_USO_CFDI, default='G03')
    objeto_impuesto = models.CharField(
        max_length=2, choices=CHOISE_OBJETO_IMPUESTO, default='02',
        help_text="Objeto de impuesto (IVA) que se usará por default al timbrar sus facturas."
    )
    email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    tipo_contribuyente = models.CharField(max_length=100, choices=CHOISE_TIPO_CONTRIBUYENTE, blank=True, null=True)
    direccion_domicilio = models.TextField(max_length=255, blank=True, null=True)
    factura_global = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre}"

    class Meta:
        unique_together = ('empresa', 'rfc')    