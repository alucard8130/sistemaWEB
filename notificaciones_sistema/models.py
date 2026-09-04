from django.conf import settings
from django.db import models


class NotificacionSistema(models.Model):
    TIPO_CHOICES = [  # noqa: RUF012
        ('promocion', 'Promoción'),
        ('nueva_funcion', 'Nueva función'),
        ('mejora', 'Actualización sistema'),
        ('otro', 'Otro'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro')
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    TOUR_CHOICES = [  # noqa: RUF012
        ('navbar', 'Recorrido del menú principal'),
        ('facturacion', 'Recorrido de Facturación'),
        ('gastos', 'Recorrido de Gastos'),
        ('cartera', 'Recorrido de Cartera Vencida'),
    ]
    tour_a_disparar = models.CharField(
        max_length=30, choices=TOUR_CHOICES, blank=True, null=True,
        help_text="Si al hacer clic en esta notificación, también debe iniciar un tour guiado específico. Déjalo vacío si no aplica."
    )

    class Meta:
        ordering = ['-fecha_creacion']  # noqa: RUF012

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.titulo}"


class NotificacionLeida(models.Model):
    """Registra qué usuario ya vio qué notificación -- una notificación
    la puede leer mucha gente, cada quien de forma independiente."""
    notificacion = models.ForeignKey(NotificacionSistema, on_delete=models.CASCADE, related_name='lecturas')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones_sistema_leidas'
    )
    fecha_leida = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('notificacion', 'usuario')
