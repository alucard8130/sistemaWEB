
from django.db import models

class Anuncio(models.Model):
    nombre_negocio = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='anuncios/logos/', blank=True, null=True)
    imagen = models.ImageField(upload_to='anuncios/imagenes/', blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    link_pagina = models.URLField(blank=True)
    link_facebook = models.URLField(blank=True)
    link_instagram = models.URLField(blank=True)
    link_otro = models.URLField(blank=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_negocio