
# Create your models here.
from django.db import models
from empresas.models import Empresa

class Cliente(models.Model):
    id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rfc = models.CharField(max_length=13, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.rfc} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'rfc')
