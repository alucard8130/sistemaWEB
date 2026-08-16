
# Create your models here.
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum

from empleados.models import Empleado
from empresas.models import CuentaBancaria, Empresa
from proveedores.models import Proveedor


class CuentaContable(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas_contables')
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=150)
    cuenta_padre = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcuentas'
    )
    NATURALEZA_CHOICES = [  # noqa: RUF012
        ('deudora', 'Deudora'),
        ('acreedora', 'Acreedora'),
    ]
    naturaleza = models.CharField(max_length=10, choices=NATURALEZA_CHOICES, default='deudora')
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'codigo')
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    @property
    def es_cuenta_mayor(self):
        return self.cuenta_padre_id is None
    
class CargaCatalogoSesion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    ESTADO_CHOICES = [  # noqa: RUF012
        ('pendiente_revision', 'Pendiente de revisión'),
        ('aplicada', 'Aplicada'),
        ('cancelada', 'Cancelada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente_revision')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

class CargaCatalogoFila(models.Model):
    sesion = models.ForeignKey(CargaCatalogoSesion, on_delete=models.CASCADE, related_name='filas')
    fila_excel = models.PositiveIntegerField()
    codigo = models.CharField(max_length=30)
    nombre_cuenta = models.CharField(max_length=150)
    codigo_padre = models.CharField(max_length=30, blank=True, null=True)
    naturaleza = models.CharField(max_length=10, default='deudora')
    grupo_nombre = models.CharField(max_length=100, blank=True, null=True)
    subgrupo_nombre = models.CharField(max_length=100, blank=True, null=True)

    # NUEVO
    uso_especial = models.CharField(max_length=30, blank=True, null=True)

    tipo_gasto_sugerido = models.ForeignKey('TipoGasto', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    similitud_pct = models.PositiveIntegerField(default=0)

    ACCION_CHOICES = [  # noqa: RUF012
        ('crear_nuevo', 'Crear nuevo tipo de gasto'),
        ('usar_existente', 'Usar tipo de gasto existente'),
        ('solo_cuenta', 'Solo cargar la cuenta (sin tipo de gasto)'),
    ]
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES, blank=True, null=True)
    tipo_gasto_elegido = models.ForeignKey('TipoGasto', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['fila_excel']


class GrupoGasto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    es_exento_iva = models.BooleanField(
        default=False,
        help_text="Actívalo para grupos como Nómina, donde los gastos NO incluyen IVA."
    )

    def __str__(self):
        return self.nombre

class SubgrupoGasto(models.Model):
    grupo = models.ForeignKey('GrupoGasto', on_delete=models.CASCADE, related_name='subgrupos')
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.grupo.nombre}/{self.nombre}"
 
    
class TipoGasto(models.Model):
    empresa= models.ForeignKey(Empresa, on_delete=models.CASCADE)
    subgrupo = models.ForeignKey(SubgrupoGasto, on_delete=models.CASCADE, related_name='tipos')
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True)
    # NUEVO — homologación con el catálogo de cuentas contables del cliente
    cuenta_contable = models.ForeignKey(
        CuentaContable, on_delete=models.SET_NULL, null=True, blank=True, related_name='tipos_gasto'
    )

    def __str__(self):
        return f"{self.subgrupo.nombre}/{self.nombre}"

class Gasto(models.Model):
    empresa = models.ForeignKey(Empresa,on_delete=models.CASCADE,null=True,blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_gasto = models.ForeignKey(TipoGasto, on_delete=models.PROTECT)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    comprobante = models.FileField(upload_to='cfdi_gastos/', blank=True, null=True)
    folio_comprobante = models.CharField(max_length=100, blank=True, null=True, 
                                      help_text='Folio o número de la factura/comprobante adjunto')
    STATUS_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    estatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True)
    retencion_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retencion_isr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.fecha} - {self.tipo_gasto} - ${self.monto}"  

    @property
    def total_pagado(self):
        return sum(p.monto for p in self.pagos.all())

    @property
    def saldo_restante(self):
        total_pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
        return self.monto - total_pagado

    
    def actualizar_estatus(self):
        total_pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
        if total_pagado >= self.monto:
            self.estatus = 'pagada'
        elif total_pagado == 0:
            self.estatus = 'pendiente'
        else:
            self.estatus = 'pendiente'  # O podrías poner un "parcial" si agregas esa opción
        self.save()
   
        

class PagoGasto(models.Model):
    gasto = models.ForeignKey('Gasto', on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    forma_pago = models.CharField(
        max_length=30,
        choices=[('transferencia', 'Transferencia'),('efectivo', 'Efectivo') , ('cheque', 'Cheque'), ('tarjeta', 'Tarjeta')],
        default='transferencia'
    )
    referencia = models.CharField(max_length=100, blank=True, null=True)
    comprobante = models.FileField(upload_to='comprobante_gastos/', blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.PROTECT, related_name='pagos_gastos', default=None, null=True, blank=True)

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago de ${self.monto} para solicitud {self.gasto.id}'


