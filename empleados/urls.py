from django.urls import path

from empleados import reportes, views_asistencia
from . import views

urlpatterns = [
    path('', views.empleado_lista, name='empleado_lista'),
    path('nuevo/', views.empleado_crear, name='empleado_crear'),
    path('editar/<int:pk>/', views.empleado_editar, name='empleado_editar'),
    path('marcar/<uuid:token>/', views_asistencia.marcar_asistencia, name='marcar_asistencia'),
    path('marcar/<uuid:token>/entrada/', views_asistencia.api_marcar_entrada, name='api_marcar_entrada'),
    path('marcar/<uuid:token>/salida/', views_asistencia.api_marcar_salida, name='api_marcar_salida'),

     # Reporte (requiere login, cualquier usuario de la empresa)
    path('reporte/', reportes.reporte_asistencia, name='reporte_asistencia'),
    path('reporte/exportar/', reportes.exportar_reporte_asistencia, name='exportar_reporte_asistencia'),
    path('reporte/detectar-faltas/', reportes.detectar_faltas_manual, name='detectar_faltas_manual'),
]
