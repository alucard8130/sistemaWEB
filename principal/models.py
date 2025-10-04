
from django.contrib.auth.models import User, AbstractUser
from django.db import models
from areas.models import AreaComun
from empresas.models import Empresa
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from locales.models import LocalComercial
from django import forms

#perfil de usuario extendido
class PerfilUsuario(models.Model):
    TIPO_USUARIOS = [
        ('demo', 'Demo'),
        ('pago', 'Pago'),
        ('gratis', 'Gratis'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIOS, default='demo')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    mostrar_wizard = models.BooleanField(default=False)
    
    def __str__(self):
       return f"{self.usuario.username} → {self.empresa.nombre if self.empresa else 'Sin empresa'}"

# Modulo de auditoria 
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

# Modulo de eventos y notificaciones    
class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE) 
    titulo = models.CharField(max_length=200)
    fecha = models.DateField()
    descripcion = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_correo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.titulo} ({self.fecha})"    
    

# Modulo de tickets de mantenimiento

class TicketMantenimiento(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('resuelto', 'Resuelto'),
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    empleado_asignado = models.ForeignKey('empleados.Empleado', on_delete=models.SET_NULL, null=True, related_name='tickets_asignados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    solucion = models.TextField(blank=True, null=True)
    fecha_solucion = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.titulo} ({self.get_estado_display()})"    

class SeguimientoTicket(models.Model):
    ticket = models.ForeignKey('TicketMantenimiento', on_delete=models.CASCADE, related_name='seguimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comentario = models.TextField()

    def __str__(self):
        return f"Seguimiento {self.fecha} - {self.usuario}"    

# Modulo de acceso para visitantes    
class VisitanteAcceso(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # Guarda hash, no texto plano
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    locales = models.ManyToManyField(LocalComercial, blank=True, verbose_name="Locales")
    areas = models.ManyToManyField(AreaComun, blank=True, verbose_name="Áreas comunes")

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username        

# Modulo de votaciones por correo electrónico    
class TemaGeneral(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

class VotacionCorreo(models.Model):
    VOTO_CHOICES = (
        ('si', 'Sí'),
        ('no', 'No'),
        ('abstencion', 'Abstención'),
    )
    tema = models.ForeignKey(TemaGeneral, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    voto = models.CharField(max_length=20, choices=VOTO_CHOICES, null=True, blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_voto = models.DateTimeField(null=True, blank=True)

    def ya_voto(self):
        return self.voto is not None    