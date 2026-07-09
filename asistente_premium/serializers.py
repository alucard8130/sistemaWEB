"""Serializadores para la API REST"""
from rest_framework import serializers
from .models import ConversacionAsistente, MensajeAsistente


class MensajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensajeAsistente
        fields = ['id', 'tipo', 'contenido', 'opciones', 'fecha_creacion']


class ConversacionSerializer(serializers.ModelSerializer):
    mensajes = MensajeSerializer(source='mensajes_historial', many=True, read_only=True)
    
    class Meta:
        model = ConversacionAsistente
        fields = [
            'id', 'intencion', 'estado', 'datos_recopilados', 
            'errores', 'mensajes', 'fecha_inicio', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_inicio', 'fecha_actualizacion']