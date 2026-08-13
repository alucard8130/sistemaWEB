"""Admin para el asistente"""
from django.contrib import admin

from .models import ConversacionAsistente, MensajeAsistente


@admin.register(ConversacionAsistente)
class ConversacionAsistenteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'intencion', 'estado', 'fecha_inicio']  # noqa: RUF012
    list_filter = ['estado', 'intencion', 'fecha_inicio']  # noqa: RUF012
    search_fields = ['usuario__nombre']  # noqa: RUF012
    readonly_fields = ['fecha_inicio', 'fecha_actualizacion', 'fecha_finalizacion']  # noqa: RUF012


@admin.register(MensajeAsistente)
class MensajeAsistenteAdmin(admin.ModelAdmin):
    list_display = ['conversacion', 'tipo', 'fecha_creacion']  # noqa: RUF012
    list_filter = ['tipo', 'fecha_creacion']  # noqa: RUF012
    readonly_fields = ['fecha_creacion']  # noqa: RUF012
