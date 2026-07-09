"""Admin para el asistente"""
from django.contrib import admin
from .models import ConversacionAsistente, MensajeAsistente


@admin.register(ConversacionAsistente)
class ConversacionAsistenteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'intencion', 'estado', 'fecha_inicio']
    list_filter = ['estado', 'intencion', 'fecha_inicio']
    search_fields = ['usuario__nombre']
    readonly_fields = ['fecha_inicio', 'fecha_actualizacion', 'fecha_finalizacion']


@admin.register(MensajeAsistente)
class MensajeAsistenteAdmin(admin.ModelAdmin):
    list_display = ['conversacion', 'tipo', 'fecha_creacion']
    list_filter = ['tipo', 'fecha_creacion']
    readonly_fields = ['fecha_creacion']