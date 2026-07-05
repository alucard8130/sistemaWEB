from django.db import models
from django.contrib.auth.models import User
from empresas.models import Empresa


class UsuarioAcceso(models.Model):
    TIPO_CHOICES = [
        ('administradora', 'Empresa Administradora'),
        ('comite', 'Comité / Mesa Directiva'),
    ]
    PLAN_CHOICES = [
        ('basico', 'Básico — 1 empresa — $299/mes'),
        ('profesional', 'Profesional — hasta 3 empresas — $699/mes'),
        ('enterprise', 'Enterprise — ilimitadas — $1,499/mes'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='usuario_acceso')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basico')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=False)  # False hasta que pague
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    nombre_organizacion = models.CharField(max_length=100, blank=True, null=True,
        help_text="Nombre de la empresa administradora o del comité")
    telefono = models.CharField(max_length=15, blank=True, null=True)

    @property
    def limite_empresas(self):
        limites = {
            'basico': 1,
            'profesional': 3,
            'enterprise': 9999,
        }
        return limites.get(self.plan, 1)

    @property
    def puede_agregar_empresa(self):
        return self.accesos_empresas.filter(activo=True).count() < self.limite_empresas

    @property
    def empresas_activas(self):
        return Empresa.objects.filter(
            accesos_usuarios__usuario_acceso=self,
            accesos_usuarios__activo=True,
            accesos_usuarios__aprobado=True,
        )

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = 'Usuario de acceso'
        verbose_name_plural = 'Usuarios de acceso'


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

    # Permisos de reportes configurables por el superusuario
    ver_dashboard = models.BooleanField(default=False)
    ver_estado_resultados = models.BooleanField(default=False)
    ver_cobranza = models.BooleanField(default=False)
    ver_gastos = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario_acceso} → {self.empresa.nombre} ({self.get_estado_display()})"

    class Meta:
        unique_together = ('usuario_acceso', 'empresa')
        verbose_name = 'Acceso a empresa'
        verbose_name_plural = 'Accesos a empresas'