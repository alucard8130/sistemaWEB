from django.db import models

from empleados.models import Empleado
from empresas.models import CuentaBancaria


class FondeoCajaChica(models.Model):
    ORIGEN_CHOICES = [  # noqa: RUF012
        ('banco', 'Banco (cheque / transferencia)'),
        ('cobros_efectivo', 'Cobros en efectivo'),
    ]
    FUENTE_CHOICES = [  # noqa: RUF012
        ('ipc', 'IPC (cursos, talleres, transporte, uniformes)'),
        ('cafeteria', 'Cafetería'),
        ('colegiaturas', 'Colegiaturas / inscripciones'),
    ]

    empresa = models.ForeignKey(
        "empresas.Empresa", on_delete=models.CASCADE, null=True, blank=True
    )
    numero_cheque = models.CharField(max_length=50)
    importe_cheque = models.DecimalField(max_digits=10, decimal_places=2)
    # NUEVO -- null/blank: los fondeos por cobros en efectivo no tienen
    # responsable (la caja la maneja el dueno) ni cuenta bancaria.
    # El formulario de fondeo normal sigue exigiendolos (ver forms.py).
    empleado_asignado = models.ForeignKey(
        Empleado, on_delete=models.CASCADE, null=True, blank=True
    )
    fecha = models.DateField()
    saldo = models.DecimalField(max_digits=10, decimal_places=2)
    cuenta_bancaria = models.ForeignKey(
        CuentaBancaria,
        on_delete=models.PROTECT,
        related_name='fondeos_caja_chica',
        null=True,
        blank=True,
    )
    # NUEVO -- permite distinguir de donde viene el dinero de la caja.
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default='banco', db_index=True
    )
    fuente = models.CharField(
        max_length=20, choices=FUENTE_CHOICES, blank=True, default=''
    )
 
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
