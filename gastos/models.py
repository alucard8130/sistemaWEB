
# Create your models here.
from django.db import models

class GrupoGasto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class SubgrupoGasto(models.Model):
    grupo = models.ForeignKey('GrupoGasto', on_delete=models.CASCADE, related_name='subgrupos')
    nombre = models.CharField(max_length=100)

    class Meta:
        unique_together = ('grupo', 'nombre')
        verbose_name = "Subgrupo de Gasto"
        verbose_name_plural = "Subgrupos de Gasto"

    def __str__(self):
        return f"{self.grupo} / {self.nombre}"

class TipoGasto(models.Model):
    subgrupo = models.ForeignKey(SubgrupoGasto, on_delete=models.CASCADE, related_name='tipos')
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.subgrupo} - {self.nombre}"