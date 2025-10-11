
# Create your models here.
from django.db import models
from empresas.models import Empresa

class Cliente(models.Model):
    CHOSE_REGIMEN_FISCAL = [
        ('601', 'General de Ley Personas Morales'),
        ('603', 'Personas Morales con Fines no Lucrativos'),
        ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
        ('606', 'Arrendamiento'),
        ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
        ('616', 'Sin obligaciones fiscales'),
        ('621', 'Incorporación Fiscal'),
        ('626', 'Régimen Simplificado de Confianza'),
    ]
    CHOSE_USO_CFDI = [
        ('G03', 'Gastos en general'),
        ('S01', 'Sin efectos fiscales'),
    ]
    id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rfc = models.CharField(max_length=13, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    regimen_fiscal = models.CharField(max_length=100, choices=CHOSE_REGIMEN_FISCAL, blank=True, null=True)
    uso_cfdi = models.CharField(max_length=100, choices=CHOSE_USO_CFDI, default='G03')
    email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre}"
        #return f"{self.nombre} {self.rfc} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'rfc')
