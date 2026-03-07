# Create your models here.
from django.db import models
from empresas.models import Empresa
from facturacion.models import Factura  # Ajusta el import según tu proyecto

class EstadoCuenta(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=20)
    archivo = models.FileField(upload_to='estados_cuenta/')
    fecha_carga = models.DateTimeField(auto_now_add=True)

class MovimientoBancario(models.Model):
    estado_cuenta = models.ForeignKey(EstadoCuenta, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateField()
    descripcion = models.CharField(max_length=255)
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=[('cargo', 'Cargo'), ('abono', 'Abono')])
    identificado = models.BooleanField(default=False)
    factura = models.ForeignKey(Factura, null=True, blank=True, on_delete=models.SET_NULL)
    deposito_por_identificar = models.BooleanField(default=False)