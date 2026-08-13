
# Create your models here.
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

from areas.models import AreaComun
from clientes.models import Cliente
from empresas.models import CuentaBancaria, Empresa
from locales.models import LocalComercial


class Factura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    local = models.ForeignKey(LocalComercial, on_delete=models.SET_NULL, null=True, blank=True)
    area_comun = models.ForeignKey(AreaComun, on_delete=models.SET_NULL, null=True, blank=True)
    TIPO_CUOTA_CHOICES = [  # noqa: RUF012
        ('mantenimiento', 'Mantenimiento'),
        ('renta', 'Renta'),
        ('deposito', 'Deposito Garantía'),
        ('extraordinaria', 'Extraordinaria'),
        ('penalidad', 'Multa'),
        ('intereses', 'Intereses'),
    ]   
    tipo_cuota= models.CharField(max_length=100, choices=TIPO_CUOTA_CHOICES)
    folio = models.CharField(max_length=100)
    uuid= models.CharField(max_length=100, blank=True, null=True)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    monto = models.DecimalField(max_digits=20, decimal_places=2)
    STATUS_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente'),
        ('cobrada', 'Cobrada'),
        ('cancelada', 'Cancelada'),
    ]
    estatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    facturama_id = models.CharField(max_length=100, blank=True, null=True)
    factura_global = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='facturas_incluidas'
    )
    locales_incluidos = models.ManyToManyField(
        'locales.LocalComercial', blank=True, related_name='facturas_grupo',
        help_text="Para facturas consolidadas de un grupo: todos los locales que cubre esta factura."
    )
    pool_vacancia = models.ForeignKey(
            "facturacion.PoolVacancia", null=True, blank=True, on_delete=models.SET_NULL,
            related_name="facturas_generadas",
        )

    

    
    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"
    
    class Meta:
        ordering = ['-fecha_emision']
        unique_together = ('folio', 'empresa')  # Folio único por empresa
    
  
    @property
    def total_pagado(self):
        return sum(pago.monto for pago in self.pagos.all())
    
    @property
    def saldo_pendiente(self):
        if self.estatus == 'cancelada':
            return 0
        if self.estatus in ('cobrada', 'pendiente'):
            return float(self.monto) - float(self.total_pagado)
        return 0
  

    def actualizar_estatus(self):
        total_pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
       
        if total_pagado >= self.monto:
            self.estatus = 'cobrada'
        elif total_pagado == 0:
            self.estatus = 'pendiente'
        else:
            self.estatus = 'pendiente'  # O podrías poner un "parcial" si agregas esa opción
        self.save()

# En facturacion/models.py, junto a la clase Factura

class TipoCuotaHomologacion(models.Model):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='homologaciones_cuota')
    tipo_cuota = models.CharField(max_length=100, choices=Factura.TIPO_CUOTA_CHOICES)
    cuenta_contable = models.ForeignKey(
        'gastos.CuentaContable', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    class Meta:
        unique_together = ('empresa', 'tipo_cuota')

    def __str__(self):
        return f"{self.get_tipo_cuota_display()} → {self.cuenta_contable}"
    

class Pago(models.Model):

    FORMAS_PAGO = [  # noqa: RUF012
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('nota_credito', 'Nota de Crédito'),
        ('deposito', 'Depósito'),
        ('efectivo', 'Efectivo'),
        ('stripe', 'Stripe'),
        ('rendimiento_inversion', 'Rendimiento Inv.'),
        ('saldo_a_favor', 'Saldo a Favor (pago adelantado)'),  
        ('otro', 'Otro'),
    ]
    factura = models.ForeignKey('Factura', on_delete=models.CASCADE, related_name='pagos',null=True, blank=True)
    fecha_pago = models.DateField()
    monto = models.DecimalField(max_digits=20, decimal_places=2)
    forma_pago = models.CharField(max_length=100, choices=FORMAS_PAGO, default='transferencia')
    comprobante = models.FileField(upload_to='comprobantes/', blank=True, null=True)
    registrado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    identificado= models.BooleanField(default=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.PROTECT, related_name='pagos', default=None, null=True, blank=True)

    def __str__(self):
        if self.factura:
            return f"Pago de ${self.monto} a {self.factura.folio} el {self.fecha_pago}"
        return f"Deposito por identificar de ${self.monto} el {self.fecha_pago}"
    

 #modulo otros ingresos   

class FacturaOtrosIngresos(models.Model):
    empresa= models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    tipo_ingreso = models.ForeignKey('TipoOtroIngreso', on_delete=models.PROTECT)
    folio = models.CharField(max_length=50)
    uuid= models.CharField(max_length=100, blank=True, null=True)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estatus = models.CharField(max_length=20, choices=[('pendiente','Pendiente'),('cobrada','Cobrada'),('cancelada','Cancelada')], default='pendiente')
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    facturama_id = models.CharField(max_length=100, blank=True, null=True)  # Nuevo campo para almacenar el ID de Facturama

    def __str__(self):
        return f"{self.folio} - {self.cliente.nombre}"
    
    class Meta:
        unique_together = ('folio', 'empresa')  # Folio único por empresa
   
    @property
    def saldo(self):
        if self.estatus == 'cancelada':
            return Decimal('0')
        if self.estatus in ('cobrada', 'pendiente'):
            return self.monto - self.total_cobrado
        return Decimal('0')

    @property
    def total_cobrado(self):    
        return sum(c.monto for c in self.cobros.all())
    
    def actualizar_estatus(self):
        total_cobrado = self.cobros.aggregate(total=Sum('monto'))['total'] or 0

        if total_cobrado >= self.monto:
            self.estatus = 'cobrada'
        elif total_cobrado == 0:
            self.estatus = 'pendiente'
        else:
            self.estatus = 'pendiente'  # O podrías poner un "parcial" si agregas esa opción
        self.save()

class CobroOtrosIngresos(models.Model):
    FORMAS_PAGO = [  # noqa: RUF012
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('nota_credito', 'Nota de Crédito'),
        ('deposito', 'Depósito'),
        ('efectivo', 'Efectivo'),
        ('otro', 'Otro'),
    ]
    factura = models.ForeignKey(FacturaOtrosIngresos, on_delete=models.CASCADE, related_name='cobros')
    fecha_cobro = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    forma_cobro = models.CharField(max_length=20, choices=FORMAS_PAGO, default='transferencia')
    comprobante = models.FileField(upload_to='comprobantes_oi/', blank=True, null=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.PROTECT, related_name='cobros_oi',default=None, null=True, blank=True)

    def __str__(self):
        return f"Cobro de ${self.monto} para {self.factura.folio} el {self.fecha_cobro}"
    
class TipoOtroIngreso(models.Model):
    nombre = models.CharField(max_length=100)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cuenta_contable = models.ForeignKey(
        'gastos.CuentaContable', on_delete=models.SET_NULL, null=True, blank=True, related_name='tipos_otro_ingreso'
    )

    def __str__(self):
        return self.nombre


#Clase para agrupar facturas por cliente y empresa, útil para generar reportes y análisis de facturación.    
class GrupoFacturacion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='grupos_facturacion')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='grupos_facturacion')
    nombre = models.CharField(max_length=100, help_text="Ej. 'Tiendas Soriana — Plaza Norte'")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.cliente.nombre})"


#CLASE PARA AGRUPAR LOCALES VACIOS Y FACTURARLOS A UN CLIENTE ESPECIFICO, UTIL PARA FACTURACION DE VACANCIA
class PoolVacancia(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="pools_vacancia")
    cliente_cobertura = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="pools_vacancia_cubiertos",
        help_text="Cliente al que se le factura por los locales de este pool que estén vacíos cada mes.",
    )
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} — cubre: {self.cliente_cobertura.nombre}"


# Clase para manejar saldos a favor de clientes, es decir, pagos adelantados que aún no se pueden aplicar a facturas futuras.
class SaldoAFavor(models.Model):
    """Dinero que un cliente ya pagó de más (pago adelantado de varios
    meses) y que todavía no se puede aplicar porque las facturas futuras
    aún no existen -- GESAC solo genera la factura del mes en curso.

    Se aplica automáticamente, mes por mes, la próxima vez que se genere
    una factura para ese mismo cliente + propiedad, hasta agotarse.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='saldos_a_favor')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='saldos_a_favor')

    # Opcional -- si se deja vacío, el saldo aplica a CUALQUIER propiedad
    # de ese cliente (útil si el cliente solo tiene una propiedad). Si el
    # cliente tiene varias, lo normal es especificar a cuál corresponde
    # el pago adelantado, para no aplicarlo por error a otra.
    local = models.ForeignKey(
        'locales.LocalComercial', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='saldos_a_favor'
    )
    area_comun = models.ForeignKey(
        'areas.AreaComun', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='saldos_a_favor'
    )

    monto_original = models.DecimalField(max_digits=20, decimal_places=2)
    monto_disponible = models.DecimalField(max_digits=20, decimal_places=2)

    fecha_registro = models.DateField()
    origen_pago = models.ForeignKey(
        'Pago', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='saldo_a_favor_generado',
        help_text="El depósito original (sin factura) que dio origen a este saldo."
    )
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    registrado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    activo = models.BooleanField(default=True)  # se pone False solo cuando monto_disponible llega a 0

    def __str__(self):
        propiedad = self.local.numero if self.local else (self.area_comun.numero if self.area_comun else "cualquier propiedad")
        return f"Saldo a favor -- {self.cliente.nombre} ({propiedad}) -- ${self.monto_disponible} disponible"

    class Meta:
        ordering = ['fecha_registro']  # FIFO: el saldo más antiguo se consume primero    