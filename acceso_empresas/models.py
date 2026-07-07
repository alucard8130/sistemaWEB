from django.db import models
from django.contrib.auth.models import User
from empresas.models import Empresa
import secrets
from django.contrib.auth.hashers import make_password, check_password



class UsuarioAcceso(models.Model):
    TIPO_CHOICES = [
        ('administradora', 'Empresa Administradora'),
        ('comite', 'Comité / Mesa Directiva'),
    ]
    PLAN_CHOICES = [
        ('basico', 'Básico — 1 condominio'),
        ('profesional', 'Profesional — hasta 3 condominios'),
        ('enterprise', 'Enterprise — condominios ilimitados'),
    ]
    # Datos de acceso propios — sin User de Django
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    nombre_organizacion = models.CharField(max_length=100, blank=True, null=True)

    # Plan y tipo
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basico')

    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)

    # Estado
    activo = models.BooleanField(default=False)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Campos para reset de contraseña
    reset_token = models.CharField(max_length=64, blank=True, null=True)
    reset_token_expira = models.DateTimeField(null=True, blank=True)
    

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def limite_empresas(self):
        return {'basico': 1, 'profesional': 3, 'enterprise': 99}.get(self.plan, 1)

    @property
    def puede_agregar_empresa(self):
        return self.accesos_empresas.filter(activo=True).count() < self.limite_empresas

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = 'Usuario de acceso'
        verbose_name_plural = 'Usuarios de acceso'


class TokenAcceso(models.Model):
    """Token de sesión para UsuarioAcceso"""
    usuario = models.OneToOneField(UsuarioAcceso, on_delete=models.CASCADE, related_name='token')
    key = models.CharField(max_length=40, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_key():
        return secrets.token_hex(20)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)


class AccesoEmpresa(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de aprobación'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('suspendido', 'Suspendido'),
    ]
    usuario_acceso = models.ForeignKey(
        UsuarioAcceso, on_delete=models.CASCADE, related_name='accesos_empresas'
    )
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name='accesos_usuarios'
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    aprobado = models.BooleanField(default=False)
    aprobado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='accesos_aprobados'
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    ver_dashboard = models.BooleanField(default=False)
    ver_estado_resultados = models.BooleanField(default=False)
    ver_cobranza = models.BooleanField(default=False)
    ver_gastos = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario_acceso} → {self.empresa.nombre}"

    class Meta:
        unique_together = ('usuario_acceso', 'empresa')