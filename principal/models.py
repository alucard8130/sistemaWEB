
from django.contrib.auth.models import User
from django.db import models
from empresas.models import Empresa
from django.conf import settings

# Create your models here.
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
       return f"{self.usuario.username} → {self.empresa.nombre if self.empresa else 'Sin empresa'}"
    
class AuditoriaCambio(models.Model):
    MODELOS_AUDITABLES = [
        ('local', 'Local Comercial'),
        ('area', 'Área Común'),
        ('factura', 'Factura'),
    ]
    modelo = models.CharField(max_length=20, choices=MODELOS_AUDITABLES)
    objeto_id = models.PositiveIntegerField()
    campo = models.CharField(max_length=100)
    valor_anterior = models.TextField(null=True, blank=True)
    valor_nuevo = models.TextField(null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.get_modelo_display()} {self.objeto_id} - {self.campo}'
    
class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # <--- NUEVO
    titulo = models.CharField(max_length=200)
    fecha = models.DateField()
    descripcion = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_correo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.titulo} ({self.fecha})"    