from rest_framework import serializers
from .models import Anuncio


class AnuncioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anuncio
        fields = [
            'id', 'nombre_negocio', 'descripcion', 'telefono', 'email',
            'link_pagina', 'link_facebook', 'link_instagram', 'link_otro',
            'activo', 'fecha_publicacion'
        ]