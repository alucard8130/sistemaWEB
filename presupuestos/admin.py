from django.contrib import admin

from presupuestos.models import PresupuestoIngreso

# Register your models here.
@admin.register(PresupuestoIngreso)
class PresupuestoIngresoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'anio', 'mes', 'origen', 'monto_presupuestado')
    list_filter = ('empresa', 'anio', 'origen')
    search_fields = ('empresa__nombre',)