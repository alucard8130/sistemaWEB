from django.db import models

# Create your models here.
class Empresa(models.Model):
    BANCOS_CHOICES = [
        ('BANAMEX', 'Banamex'),
        ('BANCOMER', 'Bancomer'),
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
        ('OTRO', 'Otro'),
    ]
    nombre = models.CharField(max_length=100)
    rfc = models.CharField(max_length=13, unique=True)
    cuenta_bancaria = models.CharField(max_length=100, choices=BANCOS_CHOICES, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    direccion = models.TextField()
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    stripe_public_key = models.CharField(max_length=255, blank=True, null=True)
    stripe_secret_key = models.CharField(max_length=255, blank=True, null=True)
    stripe_webhook_secret = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre