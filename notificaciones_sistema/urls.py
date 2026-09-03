
from django.urls import path

from . import views

urlpatterns = [
    path('nueva/', views.crear_notificacion_sistema, name='crear_notificacion_sistema'),
    path('', views.lista_notificaciones_sistema, name='lista_notificaciones_sistema'),
    path('<int:notif_id>/desactivar/', views.desactivar_notificacion_sistema, name='desactivar_notificacion_sistema'),
    path('<int:notif_id>/leida-ajax/', views.notif_sistema_marcar_leida_ajax, name='notif_sistema_marcar_leida_ajax'),
    path('marcar-todas-ajax/', views.notif_sistema_marcar_todas_leidas_ajax, name='notif_sistema_marcar_todas_leidas_ajax'),
]