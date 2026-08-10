import random
import string
import uuid

from django.conf import settings
from django.db import models

from empresas.models import Empresa
from facturacion.models import FacturaOtrosIngresos  # ajusta el import real


class LoteToallas(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='lotes_toallas')
    codigo_barras = models.CharField(max_length=50)
    cantidad_inicial = models.PositiveIntegerField()
    cantidad_disponible = models.PositiveIntegerField()
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    recibido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['fecha_recepcion']  # FIFO: se vende primero el lote más viejo  # noqa: RUF012

    def __str__(self):
        return f"{self.codigo_barras} — {self.cantidad_disponible}/{self.cantidad_inicial} disponibles"

    
class GafeteAcceso(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='gafetes_acceso')
    numero = models.CharField(max_length=20, editable=False)
    nombre_titular = models.CharField(max_length=150)
    local = models.ForeignKey(
        'locales.LocalComercial', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gafetes_acceso',
    )
    area_comun = models.ForeignKey(
        'areas.AreaComun', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gafetes_acceso',
    )
    activo = models.BooleanField(default=True)
    fecha_alta = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'numero')
        ordering = ['numero']  # noqa: RUF012

    def __str__(self):
        origen = self.local.numero if self.local else (self.area_comun.numero if self.area_comun else '')
        return f"{self.numero} — {self.nombre_titular} ({origen})"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generar_siguiente_numero()
        super().save(*args, **kwargs)

    def _generar_siguiente_numero(self):
        ultimo = (
            GafeteAcceso.objects.filter(empresa=self.empresa)
            .exclude(numero="")
            .order_by("-id")
            .values_list("numero", flat=True)
            .first()
        )
        if ultimo and ultimo.startswith("G-"):
            try:
                siguiente = int(ultimo.replace("G-", "")) + 1
            except ValueError:
                siguiente = GafeteAcceso.objects.filter(empresa=self.empresa).count() + 1
        else:
            siguiente = GafeteAcceso.objects.filter(empresa=self.empresa).count() + 1
        return f"G-{siguiente:04d}"  

    
class CasetaOperador(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='casetas_sanitario')
    nombre = models.CharField(max_length=100, help_text="Ej. 'Caseta Principal', 'Estacionamiento Sur'")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

    
class UsoSanitario(models.Model):
    ESTADO_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente de cobro'),
        ('cobrado', 'Cobrado'),
        ('gratis', 'Gratis (gafete)'),
        ('cancelado', 'Cancelado'),
    ]
    TIPO_CHOICES = [  # noqa: RUF012
        ('sanitario', 'Uso de Sanitario'),
        ('papel', 'Venta de Papel'),
        ('toalla', 'Venta de Toalla Sanitaria'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usos_sanitario')
    codigo = models.CharField(max_length=10, db_index=True)  # antes: max_length=6
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    monto = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    fecha_generado = models.DateTimeField(auto_now_add=True)
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    fecha_cobro = models.DateTimeField(null=True, blank=True)
    cobrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    caseta = models.ForeignKey(
        CasetaOperador, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='usos',
        help_text="Si el uso se registró desde una caseta compartida (sin login), queda aquí en vez de en generado_por/cobrado_por."
    )
    gafete = models.ForeignKey(
        GafeteAcceso, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='usos',
        help_text="Si el uso fue con gafete de acceso gratuito, se registra aquí."
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sanitario')
    lote_toallas = models.ForeignKey(
        LoteToallas, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ventas',
        help_text="Solo aplica cuando tipo='toalla' -- de qué lote salió esta venta."
    )
        

    def __str__(self):
        return f"{self.codigo} — {self.get_estado_display()}"

    class Meta:
        ordering = ['-fecha_generado']  # noqa: RUF012

    @staticmethod
    def generar_codigo_unico(empresa, tipo='sanitario'):
        for _ in range(20):
            codigo = ''.join(random.choices(string.digits, k=4))
            if not UsoSanitario.objects.filter(empresa=empresa, tipo=tipo, codigo=codigo, estado='pendiente').exists():
                return codigo
        raise Exception("No se pudo generar un código único, intenta de nuevo.")  # noqa: TRY002


class CorteSanitario(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cortes_sanitario')
    caseta = models.ForeignKey(
        'CasetaOperador', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cortes',
        help_text="Caseta a la que pertenece este corte. Vacío = movimientos generados sin caseta (login directo)."
    )
    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    total_cobrado = models.DecimalField(max_digits=10, decimal_places=2)
    factura = models.ForeignKey(FacturaOtrosIngresos, on_delete=models.SET_NULL, null=True, blank=True)

    # Quien cerró el corte -- usuario GESAC (admin/login) O empleado (caseta sin login)
    cerrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    cerrado_por_empleado = models.ForeignKey(
        'empleados.Empleado', on_delete=models.SET_NULL, null=True, blank=True, related_name='cortes_sanitario_cerrados'
    )
    fecha_cierre = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_hora_fin']  # noqa: RUF012

    def nombre_responsable(self):
        if self.cerrado_por_empleado:
            return self.cerrado_por_empleado.nombre
        if self.cerrado_por:
            return self.cerrado_por.get_full_name() or self.cerrado_por.username
        return "—"

    def __str__(self):
        caseta_str = self.caseta.nombre if self.caseta else "Sin caseta"
        return f"{caseta_str} — {self.fecha_hora_fin.strftime('%d/%m/%Y %H:%M')}"



class BoletoFisico(models.Model):
    ESTADO_CHOICES = [  # noqa: RUF012
        ('disponible', 'Disponible'),
        ('usado', 'Usado'),
        ('cancelado', 'Cancelado'),
    ]
    TIPO_CHOICES = [  # noqa: RUF012
        ('sanitario', 'Uso de Sanitario'),
        ('papel', 'Venta de Papel'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='boletos_fisicos')
    codigo = models.CharField(max_length=10)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    uso = models.OneToOneField(UsoSanitario, on_delete=models.SET_NULL, null=True, blank=True, related_name='boleto_consumido')

    cargado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sanitario')
    
    class Meta:
        unique_together = ('empresa','tipo','codigo')  # no se puede cargar el mismo folio dos veces
        ordering = ['codigo']  # noqa: RUF012

    def __str__(self):
        return f"{self.codigo} — {self.get_estado_display()}"


