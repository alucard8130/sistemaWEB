from django.contrib import admin
from django.utils.html import format_html
from .models import Anuncio

@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ('nombre_negocio', 'logo_preview', 'imagen_preview', 'activo', 'fecha_publicacion')
    list_filter = ('activo',)
    search_fields = ('nombre_negocio', 'telefono', 'email')
    readonly_fields = ('fecha_publicacion', 'logo_preview', 'imagen_preview')

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height:40px;"/>', obj.logo.url)
        return "-"
    logo_preview.short_description = "Logo"

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height:40px;"/>', obj.imagen.url)
        return "-"
    imagen_preview.short_description = "Imagen"
