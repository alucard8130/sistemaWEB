# Create your models here.
from django.db import models
from empresas.models import Empresa  # Ajusta el import según tu proyecto

class EstadoCuentaBancario(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='estados_cuenta/')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    saldo_inicial = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=14, decimal_places=2)
    total_abonos = models.DecimalField(max_digits=14, decimal_places=2)
    total_cargos = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_subida = models.DateTimeField(auto_now_add=True)

class MovimientoEstadoCuenta(models.Model):
    estado_cuenta = models.ForeignKey(EstadoCuentaBancario, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateField()
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=[('abono', 'Abono'), ('cargo', 'Cargo')])
    conciliado = models.BooleanField(default=False)
    referencia_conciliacion = models.CharField(max_length=255, blank=True, null=True)  # Para guardar con qué se concilió