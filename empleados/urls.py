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
    path('marcar/<uuid:token>/inicio_comida/', views_asistencia.api_marcar_inicio_comida, name='api_marcar_inicio_comida'),
    path('marcar/<uuid:token>/fin_comida/', views_asistencia.api_marcar_fin_comida, name='api_marcar_fin_comida'),
    path('marcar/<uuid:token>/ubicacion/', views_asistencia.api_actualizar_ubicacion, name='api_actualizar_ubicacion'),

     # Reporte (requiere login, cualquier usuario de la empresa)
    path('reporte/', reportes.reporte_asistencia, name='reporte_asistencia'),
    path('reporte/exportar/', reportes.exportar_reporte_asistencia, name='exportar_reporte_asistencia'),
    path('reporte/detectar-faltas/', reportes.detectar_faltas_manual, name='detectar_faltas_manual'),

    path('empleados/vacaciones/<int:incidencia_id>/pdf/', views.generar_solicitud_vacaciones_pdf, name='solicitud_vacaciones_pdf'),
    path('empleados/permiso/<int:incidencia_id>/pdf/', views.generar_solicitud_permiso_pdf, name='solicitud_permiso_pdf'),
    path('empleados/prestamo/<int:solicitud_id>/pdf/', views.generar_solicitud_prestamo_pdf, name='solicitud_prestamo_pdf'),
    path('empleados/prestamo/nuevo/', views.solicitud_prestamo_crear, name='solicitud_prestamo_crear'),
    path('empleados/prestamos/', views.solicitudes_prestamo_lista, name='solicitudes_prestamo_lista'),
    path('empleados/prestamos/<int:solicitud_id>/estatus/', views.solicitud_prestamo_cambiar_estatus, name='solicitud_prestamo_cambiar_estatus'), 

   
]
