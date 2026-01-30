from django.db import models
from empleados.models import Empleado


class FondeoCajaChica(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa", on_delete=models.CASCADE, null=True, blank=True
    )
    numero_cheque = models.CharField(max_length=50)
    importe_cheque = models.DecimalField(max_digits=10, decimal_places=2)
    empleado_asignado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha = models.DateField()
    saldo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Cheque {self.numero_cheque} - Saldo: {self.saldo}"


class GastoCajaChica(models.Model):
    fondeo = models.ForeignKey(FondeoCajaChica, on_delete=models.CASCADE)
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", on_delete=models.SET_NULL, null=True, blank=True
    )
    tipo_gasto = models.ForeignKey(
        "gastos.TipoGasto", on_delete=models.SET_NULL, null=True, blank=True
    )
    descripcion = models.TextField()
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()

    

    def __str__(self):
        return f"Gasto {self.descripcion} - Importe: {self.importe}"


class ValeCaja(models.Model):
    fondeo = models.ForeignKey(FondeoCajaChica, on_delete=models.CASCADE)
    tipo_gasto = models.ForeignKey(
        "gastos.TipoGasto", on_delete=models.SET_NULL, null=True, blank=True
    )
    descripcion = models.TextField()
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    recibido_por = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    autorizado_por = models.CharField(max_length=100, null=True, blank=True)
    status=models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("comprobado", "Comprobado"),
        ],
        default="pendiente",
    )
 

    def __str__(self):
        return f"Vale {self.descripcion} - Importe: {self.importe}"
