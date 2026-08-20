
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_cobranza, name='dashboard_cobranza'),
    path('resumen-portal/', views.resumen_cobranza_portal, name='resumen_cobranza_portal'),
    path('expediente/<int:expediente_id>/', views.detalle_expediente, name='detalle_expediente'),
    path('expediente/<int:expediente_id>/registrar-gestion/', views.registrar_gestion, name='registrar_gestion'),
    path('expediente/<int:expediente_id>/enviar-mensaje/', views.enviar_mensaje_plantilla, name='enviar_mensaje_plantilla'),
    path('expediente/<int:expediente_id>/carta-extrajudicial/<int:plantilla_id>/', views.generar_carta_extrajudicial_pdf, name='generar_carta_extrajudicial_pdf'),
    path('expediente/<int:expediente_id>/plan-pago/nuevo/', views.crear_plan_pago, name='crear_plan_pago'),
    path('plan-pago/<int:plan_id>/', views.detalle_plan_pago, name='detalle_plan_pago'),
    path('parcialidad/<int:parcialidad_id>/marcar-pagada/', views.marcar_parcialidad_pagada, name='marcar_parcialidad_pagada'),
    path('expediente/<int:expediente_id>/cambiar-etapa/', views.cambiar_etapa_expediente, name='cambiar_etapa_expediente'),
    path('expediente/<int:expediente_id>/asignar/', views.asignar_expediente, name='asignar_expediente'),
    path('expediente/<int:expediente_id>/cerrar/', views.cerrar_expediente, name='cerrar_expediente'),
    path('plantillas/', views.lista_plantillas, name='lista_plantillas'),
    path('plantillas/nueva/', views.crear_plantilla, name='crear_plantilla'),
    path('plantillas/<int:plantilla_id>/editar/', views.editar_plantilla, name='editar_plantilla'),
    path('plantillas/<int:plantilla_id>/toggle-activa/', views.toggle_activa_plantilla, name='toggle_activa_plantilla'),
]
