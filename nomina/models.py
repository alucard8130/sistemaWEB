from django.db import models

# ============================================================
# 2. Modelos nuevos -- Dispersión de Nómina
# ============================================================

class DispersionNomina(models.Model):
    """Un periodo/lote de dispersión de nómina -- agrupa los recibos
    (XML) de todos los empleados pagados en una misma corrida."""

    ESTATUS_CHOICES = [  # noqa: RUF012
        ('borrador', 'Borrador -- en revisión'),
        ('confirmado', 'Confirmado -- ya generó los gastos'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='dispersiones_nomina')
    cuenta_bancaria = models.ForeignKey(
        'empresas.CuentaBancaria', on_delete=models.PROTECT, related_name='dispersiones_nomina',
        help_text="Cuenta desde la que se dispersó la nómina -- el XML no la trae, se indica aquí."
    )
    fecha_pago = models.DateField(
        null=True, blank=True,
        help_text="Se autocompleta con la fecha de pago de los XML al subirlos, pero puedes ajustarla."
    )
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='borrador')
    registrado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    notas = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Dispersión {self.periodo_inicio} a {self.periodo_fin} — {self.empresa.nombre}"

    @property
    def total_neto(self):
        return self.recibos.aggregate(t=models.Sum('neto_pagado'))['t'] or 0


class ReciboNomina(models.Model):
    """Un recibo (XML de nómina) individual, dentro de una dispersión.
    Se cruza automáticamente contra Empleado por RFC."""

    ESTATUS_CHOICES = [  # noqa: RUF012
        ('ok', 'Encontrado — listo'),
        ('sin_match', 'RFC no encontrado — requiere asignación manual'),
        ('duplicado', 'Ya se había procesado este folio fiscal antes'),
        ('error', 'Error al leer el XML'),
    ]

    dispersion = models.ForeignKey(DispersionNomina, on_delete=models.CASCADE, related_name='recibos')
    archivo_xml = models.FileField(upload_to='nomina/xml/')

    # Datos extraídos del XML (se guardan aunque no haya match, para depurar)
    uuid_fiscal = models.CharField(max_length=36, blank=True, null=True, db_index=True)
    rfc_receptor = models.CharField(max_length=13, blank=True, null=True)
    nombre_receptor = models.CharField(max_length=255, blank=True, null=True)
    fecha_pago = models.DateField(null=True, blank=True)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    total_percepciones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deducciones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_otros_pagos = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Ej. Subsidio para el Empleo -- se le entrega al trabajador aunque no sea una percepción."
    )
    neto_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    empleado = models.ForeignKey('empleados.Empleado', on_delete=models.SET_NULL, null=True, blank=True, related_name='recibos_nomina')
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='sin_match')
    error_detalle = models.CharField(max_length=255, blank=True, null=True)

    gasto = models.ForeignKey('gastos.Gasto', on_delete=models.SET_NULL, null=True, blank=True, related_name='recibo_nomina')

    class Meta:
        ordering = ['nombre_receptor']

    def __str__(self):
        return f"{self.nombre_receptor or self.rfc_receptor or 'Recibo'} — ${self.neto_pagado}"