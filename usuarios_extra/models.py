from django.conf import settings
from django.db import models


def limite_usuarios_empresa(empresa):
    """Cuantos usuarios (PerfilUsuario) puede tener esta empresa en total,
    segun su plan actual -- incluye al dueño."""
    if empresa.es_premium:
        return 4  # dueño + 3 usuarios extra
    elif empresa.es_plus:
        return 2  # dueño + 1 usuarios extra
    return 1  # Demo/Gratis -- solo el dueño


class InvitacionUsuarioEmpresa(models.Model):
    ESTADO_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('cancelada', 'Cancelada'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='invitaciones_usuario')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    invitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='invitaciones_enviadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aceptada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']  # noqa: RUF012

    def __str__(self):
        return f"{self.email} → {self.empresa.nombre} ({self.get_estado_display()})"
