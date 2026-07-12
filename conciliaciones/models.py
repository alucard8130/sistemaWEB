from django.db import models
from django.contrib.auth.models import User

from empresas.models import CuentaBancaria, Empresa


class EstadoCuentaBancario(models.Model):
    empresa=models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='estados_cuenta/')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    nombre_original = models.CharField(max_length=255)

    def __str__(self):
        return f"Estado {self.cuenta_bancaria} {self.fecha_inicio} - {self.fecha_fin}"

class MovimientoEstadoCuenta(models.Model):
    TIPO_CHOICES = (
        ('cargo', 'Cargo'),
        ('abono', 'Abono'),
    )
    estado_cuenta = models.ForeignKey(EstadoCuentaBancario, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateField()
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    conciliado = models.BooleanField(default=False)
    movimiento_sistema = models.ForeignKey('MovimientoSistema', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.fecha} {self.tipo} {self.monto}"

class MovimientoSistema(models.Model):
    TIPO_CHOICES = (
        ('cargo', 'Cargo'),
        ('abono', 'Abono'),
    )
    empresa=models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.CASCADE)
    fecha = models.DateField()
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    conciliado = models.BooleanField(default=False)
    movimiento_estado_cuenta = models.ForeignKey(MovimientoEstadoCuenta, on_delete=models.SET_NULL, null=True, blank=True)
    origen = models.CharField(max_length=50)  # Ej: 'Pago', 'Cobro', etc.

    def __str__(self):
        return f"{self.fecha} {self.origen} {self.monto}"

class ConciliacionBancaria(models.Model):
    empresa=models.ForeignKey(Empresa, on_delete=models.CASCADE)
    estado_cuenta = models.ForeignKey(EstadoCuentaBancario, on_delete=models.CASCADE)
    fecha_conciliacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    resumen = models.JSONField()

    def __str__(self):
        return f"Conciliación {self.estado_cuenta} {self.fecha_conciliacion}"
    

class SaldoCuentaPeriodo(models.Model):
    cuenta = models.ForeignKey(
        CuentaBancaria, on_delete=models.CASCADE,
        related_name='saldos_periodo'
    )
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name='saldos_periodo'
    )
    anio = models.IntegerField()
    mes = models.IntegerField()
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_calculado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cerrado = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    cerrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    abonos_banco = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cargos_banco = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('cuenta', 'anio', 'mes')
        ordering = ['-anio', '-mes']
        verbose_name = 'Saldo por período'
        verbose_name_plural = 'Saldos por período'

    def __str__(self):
        return f"{self.cuenta} — {self.mes}/{self.anio}"

    def nombre_mes(self):
        meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                 'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        return meses[self.mes - 1]