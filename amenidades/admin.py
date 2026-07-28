from django.contrib import admin
from .models import Amenidad, Reservacion

@admin.register(Amenidad)
class AmenidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'costo_reservacion', 'activa')
    list_filter = ('empresa', 'activa')

@admin.register(Reservacion)
class ReservacionAdmin(admin.ModelAdmin):
    list_display = ('amenidad', 'cliente', 'fecha', 'hora_inicio', 'hora_fin', 'estado')
    list_filter = ('empresa', 'amenidad', 'estado')
    search_fields = ('cliente__nombre',)
