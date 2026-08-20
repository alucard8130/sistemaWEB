from django.db import models


# Create your models here.
class Empresa(models.Model):
    REGIMEN_CHOICES = [  # noqa: RUF012
        ('601', 'General de Ley Personas Morales'),
        ('603', 'Personas Morales con Fines no Lucrativos'),
        ('621', 'Incorporación Fiscal'),
        ('626', 'Régimen Simplificado de Confianza'),
    ]
    SEGMENTO_CHOICES = [  # noqa: RUF012
        ('comercial', 'Comercial (plaza / centro comercial)'),
        ('habitacional', 'Habitacional (condominio residencial)'),
    ]
    ESTADO_CHOICES = [  # noqa: RUF012
        ('activa', 'Activa'),
        ('prueba', 'En prueba'),
        ('suspendida', 'Suspendida'),
        ('cancelada', 'Cancelada'), 
        ('gratis', 'Gratis'),
    ]
    nombre = models.CharField(max_length=100)
    rfc = models.CharField(max_length=13, unique=True)
    regimen_fiscal = models.CharField(max_length=100, choices=REGIMEN_CHOICES, blank=True, null=True,default='603')
    direccion = models.TextField()
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    stripe_public_key = models.CharField(max_length=255, blank=True, null=True)
    stripe_secret_key = models.CharField(max_length=255, blank=True, null=True)
    stripe_webhook_secret = models.CharField(max_length=255, blank=True, null=True)
    es_plus = models.BooleanField(default=False)  # True = versión plus
    es_premium = models.BooleanField(default=False)  # True = versión premium, False = Plus
    # --- Ubicación para validar asistencia por GPS ---
    lat_oficina = models.DecimalField(max_digits=30, decimal_places=20, null=True, blank=True,help_text="Latitud de la oficina/caseta donde se debe marcar asistencia")
    lng_oficina = models.DecimalField(max_digits=30, decimal_places=20, null=True, blank=True,help_text="Longitud de la oficina/caseta donde se debe marcar asistencia")
    radio_permitido_metros = models.PositiveIntegerField(default=50,help_text="Radio permitido (en metros) alrededor de la ubicación para marcar asistencia válida")
    segmento = models.CharField(
        max_length=20, choices=SEGMENTO_CHOICES, default='comercial',
        help_text="Determina la terminología y opciones que ve la empresa en el sistema (Local/Renta vs. Vivienda/Amenidad)."
    )
    # NUEVO
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='activa',
        help_text="Controla si la empresa participa en procesos automáticos como la facturación mensual del Cron Job."
    )
    precio_sanitario = models.DecimalField(
            max_digits=6, decimal_places=2, null=True, blank=True,
            help_text="Precio fijo por uso de sanitario. Déjalo vacío si tu condominio no cobra este servicio."
        )
    usa_boletos_fisicos_sanitario = models.BooleanField(
        default=False,
        help_text="Si está activo, el operador captura el número del boleto físico existente en vez de que el sistema genere un código aleatorio."
    )
    precio_papel = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Precio fijo por venta de papel. Déjalo vacío si no se vende por separado."
    )
    usa_boletos_fisicos_papel = models.BooleanField(default=False) 

    precio_toalla = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Precio fijo por toalla sanitaria. Déjalo vacío si no se vende."
    )
    #Twilio configuration fields (enviar mensajes de WhatsApp y SMS)
    twilio_account_sid = models.CharField(max_length=100, blank=True, null=True)
    twilio_auth_token = models.CharField(max_length=100, blank=True, null=True)
    twilio_whatsapp_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Número de WhatsApp Business habilitado en Twilio, formato +521234567890 (sin 'whatsapp:')."
    )
    twilio_sms_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Número de Twilio para SMS, formato +521234567890."
    )

    
    def __str__(self):
        return self.nombre
    
    @property
    def es_habitacional(self):
        return self.segmento == 'habitacional'


class CuentaBancaria(models.Model):
    BANCOS_CHOICES = [  # noqa: RUF012
        ('BANAMEX', 'Banamex'),
        ('SANTANDER', 'Santander'),
        ('HSBC', 'HSBC'),
        ('BBVA', 'BBVA'),
        ('IXE', 'Ixe'),
        ('SCOTIABANK', 'Scotiabank'),
        ('BANORTE', 'Banorte'),
        ('INBURSA', 'Inbursa'),
        ('BANCOPPEL', 'Bancoppel'),
        ('AFIRME', 'Afirme'),
        ('BAJIO', 'Bajío'),
        ('MULTIVA', 'Multiva'),
        ('BANREGIO', 'Banregio'),
        ('BANJERCITO', 'Banjército'),
        ('OTRO', 'Otro'),
    ]
    TIPO_CUENTA= [  # noqa: RUF012
        ('INVERSION', 'Inversión'),
        ('CORRIENTE', 'Corriente'),
        ('NOMINA', 'Nómina'),
        ('EMPRESARIAL', 'Empresarial'),
        ('OTRO', 'Otro'),
    ]
    TIPO_MONEDA = [  # noqa: RUF012
        ('MXN', 'Peso Mexicano'),
        ('USD', 'Dólar Estadounidense'),
        ('EUR', 'Euro'),
        ('GBP', 'Libra Esterlina'),
        ('JPY', 'Yen Japonés'),
        ('OTRO', 'Otro'),   ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas_bancarias')
    banco = models.CharField(max_length=100, choices=BANCOS_CHOICES)
    numero_cuenta = models.CharField(max_length=50)
    clabe = models.CharField(max_length=18, blank=True, null=True)
    moneda = models.CharField(max_length=10, choices=TIPO_MONEDA, blank=True, null=True)
    tipo_cuenta = models.CharField(max_length=100, choices=TIPO_CUENTA, blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    activa = models.BooleanField(default=True)
    cuenta_contable = models.ForeignKey(
        'gastos.CuentaContable', on_delete=models.SET_NULL, null=True, blank=True, related_name='cuentas_bancarias'
    )
    # NUEVO -- controla si esta cuenta aparece en el PDF de referencia de
    # pago que ve el cliente. Por default True (mismo comportamiento que
    # ya tenías), pero ahora se puede desactivar por cuenta -- por
    # ejemplo, si la empresa tiene 2 cuentas y solo una es la que
    # realmente usa para cobrar cuotas.
    mostrar_en_referencia_pago = models.BooleanField(
        default=True,
        help_text="Si esta cuenta debe aparecer en el PDF de referencia de pago que recibe el cliente."
    )
    

    def __str__(self):
        return f"{self.banco} - {self.numero_cuenta}"


