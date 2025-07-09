
from django.db import models
from empresas.models import Empresa
from gastos.models import GrupoGasto, SubgrupoGasto, TipoGasto

class Presupuesto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    grupo = models.ForeignKey(GrupoGasto, on_delete=models.PROTECT)
    subgrupo = models.ForeignKey(SubgrupoGasto, on_delete=models.PROTECT, null=True, blank=True)
    tipo_gasto = models.ForeignKey(TipoGasto, on_delete=models.PROTECT, null=True, blank=True)
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField(null=True, blank=True)  # Null para anual
    monto = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = ('empresa', 'grupo', 'subgrupo', 'tipo_gasto', 'anio', 'mes')

    def __str__(self):
        periodo = f"{self.anio}"
        if self.mes:
            periodo += f"-{self.mes:02d}"
        return f"{self.empresa} | {self.grupo} | {self.tipo_gasto} | {periodo}: ${self.monto:,.2f}"

class PresupuestoCierre(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    anio = models.PositiveIntegerField()
    cerrado = models.BooleanField(default=False)
    cerrado_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('empresa', 'anio')

    def __str__(self):
        return f"{self.empresa} - {self.anio} ({'CERRADO' if self.cerrado else 'ABIERTO'})"
    
class PresupuestoIngreso(models.Model):
    ORIGEN_CHOICES = [
        ('local', 'Locales'),
        ('area', 'Áreas comunes'),
        ('otros', 'Otros ingresos'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField()
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES)
    monto_presupuestado = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('empresa', 'anio', 'mes', 'origen')

    def __str__(self):
        return f"{self.empresa} {self.get_origen_display()} {self.mes}/{self.anio}: {self.monto_presupuestado}"           