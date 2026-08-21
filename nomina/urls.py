

from django.urls import path

from . import views

urlpatterns = [
    path('dispersiones/', views.lista_dispersiones_nomina, name='lista_dispersiones_nomina'),
    path('dispersiones/nueva/', views.nueva_dispersion_nomina, name='nueva_dispersion_nomina'),
    path('dispersiones/<int:dispersion_id>/revisar/', views.revisar_dispersion_nomina, name='revisar_dispersion_nomina'),
    path('dispersiones/<int:dispersion_id>/confirmar/', views.confirmar_dispersion_nomina, name='confirmar_dispersion_nomina'),
    path('dispersiones/<int:dispersion_id>/', views.detalle_dispersion_nomina, name='detalle_dispersion_nomina'),
    path('dispersiones/exportar-excel/', views.exportar_dispersiones_nomina_excel, name='exportar_dispersiones_nomina_excel'),
    path('dispersiones/<int:dispersion_id>/borrar/', views.borrar_dispersion_nomina, name='borrar_dispersion_nomina'),
    path('dispersiones/mapeo-conceptos/', views.gestionar_mapeo_conceptos_nomina, name='gestionar_mapeo_conceptos_nomina'),
    path('dispersiones/mapeo-conceptos/<int:mapeo_id>/eliminar/', views.eliminar_mapeo_concepto_nomina, name='eliminar_mapeo_concepto_nomina'),
]
