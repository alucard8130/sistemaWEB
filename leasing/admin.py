"""Admin mínimo del segmento Arrendamiento (pantallas definitivas: fase siguiente)."""
from django.contrib import admin

from . import models as m


class EmpresaScopedAdmin(admin.ModelAdmin):
    list_filter = ("empresa",)


for nombre in (
    "ConfiguracionArrendamiento", "SincronizacionExterna", "Contraparte", "Inmueble", "CuentaPredial",
    "Unidad", "Contrato", "ContratoParte", "ContratoVersion", "ContratoUnidad", "RelacionMaestroSub",
    "ConceptoCobro", "TerminoFinanciero", "Escalador", "PartidaCalendario", "Garantia", "Obligacion",
    "Opcion", "Documento", "Incidencia", "PresupuestoMantenimiento",
):
    admin.site.register(getattr(m, nombre), EmpresaScopedAdmin)

admin.site.register(m.IndiceValor)


@admin.register(m.BitacoraAuditoria)
class BitacoraAdmin(admin.ModelAdmin):
    """Solo lectura: la bitácora es de solo anexar."""
    list_display = ("id", "empresa", "usuario", "accion", "entidad", "entidad_id", "creado_en")
    list_filter = ("empresa", "accion", "entidad")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
