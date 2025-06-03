
from django.contrib import admin
from .models import PerfilUsuario

# Register your models here.
@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa']
    search_fields = ['usuario__username', 'empresa__nombre']
