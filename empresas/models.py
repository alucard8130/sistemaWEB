from django.db import models

# Create your models here.
class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    rfc = models.CharField(max_length=13, unique=True)
    cuenta_bancaria = models.CharField(max_length=100, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    direccion = models.TextField()
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre