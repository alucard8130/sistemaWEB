from django.db import models


# Create your models here.
class Empresa(models.Model):
    REGIMEN_CHOICES = [
        ('601', 'General de Ley Personas Morales'),
        ('603', 'Personas Morales con Fines no Lucrativos'),
        ('621', 'Incorporación Fiscal'),
        ('626', 'Régimen Simplificado de Confianza'),
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
    es_plus = models.BooleanField(default=False)  # True = versión plus, False = demo
    es_premium = models.BooleanField(default=False)  # True = versión premium, False = Plus
    # --- Ubicación para validar asistencia por GPS ---
    lat_oficina = models.DecimalField(max_digits=30, decimal_places=20, null=True, blank=True,help_text="Latitud de la oficina/caseta donde se debe marcar asistencia")
    lng_oficina = models.DecimalField(max_digits=30, decimal_places=20, null=True, blank=True,help_text="Longitud de la oficina/caseta donde se debe marcar asistencia")
    radio_permitido_metros = models.PositiveIntegerField(default=150,help_text="Radio permitido (en metros) alrededor de la ubicación para marcar asistencia válida")

    def __str__(self):
        return self.nombre
    
class CuentaBancaria(models.Model):
    BANCOS_CHOICES = [
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
    TIPO_CUENTA= [
        ('INVERSION', 'Inversión'),
        ('CORRIENTE', 'Corriente'),
        ('NOMINA', 'Nómina'),
        ('EMPRESARIAL', 'Empresarial'),
        ('OTRO', 'Otro'),
    ]
    TIPO_MONEDA = [
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

    def __str__(self):
        return f"{self.banco} - {self.numero_cuenta}"

