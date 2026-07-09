from django.db import models
from django.contrib.auth.models import User
from empresas.models import Empresa
import json
from datetime import datetime

class ConversacionAsistente(models.Model):
    """Historial de conversaciones del usuario con el asistente"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_asistente')
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)

    # Intencion actual
    intencion = models.CharField(
        max_length=50,
        choices=[
            ('crear_cliente', 'Crear Cliente'),
            ('crear_proveedor', 'Crear Proveedor'),
            ('actualizar_cliente', 'Actualizar Cliente'),
            ('actualizar_proveedor', 'Actualizar Proveedor'),
            ('listar_clientes', 'Listar Clientes'),
            ('listar_proveedores', 'Listar Proveedores'),
            ('otro', 'Otro'),
        ],
        null=True,
        blank=True
    )

    # Estado de la conversación
    estado = models.CharField(
        max_length=50,
        choices=[
            ('iniciada', 'Iniciada'),
            ('solicitando_datos', 'Solicitando Datos'),
            ('validando', 'Validando'),
            ('completada', 'Completada'),
            ('cancelada', 'Cancelada'),
        ],
        default='iniciada'
    )

    # ✅ NUEVO: nombre del campo que se le está preguntando al usuario ahora mismo.
    # Sin esto, el backend no tiene forma de saber a qué campo pertenece la
    # respuesta del usuario en el siguiente mensaje.
    campo_actual = models.CharField(max_length=100, null=True, blank=True)

    # Datos recopilados (JSON)
    datos_recopilados = models.JSONField(default=dict, blank=True)

    # Errores de validación
    errores = models.JSONField(default=dict, blank=True)

    # Registro de mensajes
    mensajes = models.JSONField(default=list, blank=True)

    # Timestamps
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.get_intencion_display()} ({self.estado})"

    class Meta:
        verbose_name = 'Conversación Asistente'
        verbose_name_plural = 'Conversaciones Asistente'
        ordering = ['-fecha_actualizacion']


class MensajeAsistente(models.Model):
    """Mensajes individuales de la conversación"""
    conversacion = models.ForeignKey(ConversacionAsistente, on_delete=models.CASCADE, related_name='mensajes_historial')

    TIPO_CHOICES = [
        ('usuario', 'Usuario'),
        ('asistente', 'Asistente'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    contenido = models.TextField()

    # Opciones de respuesta (para botones)
    opciones = models.JSONField(default=list, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.contenido[:50]}"

    class Meta:
        verbose_name = 'Mensaje Asistente'
        verbose_name_plural = 'Mensajes Asistente'
        ordering = ['fecha_creacion']