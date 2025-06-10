

# Register your models here.
from django.contrib import admin
from .models import GrupoGasto, SubgrupoGasto

@admin.register(GrupoGasto)
class GrupoGastoAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']

@admin.register(SubgrupoGasto)
class SubgrupoGastoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'grupo']
    list_filter = ['grupo']
    search_fields = ['nombre']
