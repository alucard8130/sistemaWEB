
# Register your models here.
from django.contrib import admin
from .models import Factura

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['folio', 'cliente', 'fecha_emision', 'monto','tipo_cuota', 'estatus']
    search_fields = ['folio', 'cliente__nombre']
    list_filter = ['estatus', 'fecha_emision']
