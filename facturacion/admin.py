
# Register your models here.
from django.contrib import admin

from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['folio', 'cliente', 'fecha_emision', 'monto','tipo_cuota', 'estatus']  # noqa: RUF012
    search_fields = ['folio', 'cliente__nombre']  # noqa: RUF012
    list_filter = ['estatus', 'fecha_emision']  # noqa: RUF012

