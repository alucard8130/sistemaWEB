from django.contrib import admin
from django.utils.html import format_html
from .models import Empleado, Incidencia, RegistroAsistencia


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rfc", "puesto", "departamento", "activo")
    list_filter = ("puesto", "departamento", "activo")
    search_fields = ("nombre", "rfc")

    fields = (
        "empresa",
        "nombre",
        "rfc",
        "puesto",
        "departamento",
        "telefono",
        "email",
        "activo",
        "hora_entrada_esperada",
        "hora_salida_esperada",
        "tolerancia_minutos",
        "link_asistencia",
    )
    readonly_fields = ("link_asistencia",)

    def link_asistencia(self, obj):
        if not obj.pk:
            return "(guarda el empleado primero para generar su link)"
        url = obj.url_marcar_asistencia
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    link_asistencia.short_description = "Link para marcar asistencia"


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = (
        "empleado",
        "fecha",
        "hora_entrada",
        "hora_salida",
        "dentro_de_rango_entrada",
        "dentro_de_rango_salida",
    )
    list_filter = ("fecha", "dentro_de_rango_entrada", "dentro_de_rango_salida")
    search_fields = ("empleado__nombre",)
    date_hierarchy = "fecha"


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ("empleado", "tipo", "fecha", "fecha_fin", "dias", "importe")
    list_filter = ("tipo",)
    search_fields = ("empleado__nombre",)
    date_hierarchy = "fecha"
