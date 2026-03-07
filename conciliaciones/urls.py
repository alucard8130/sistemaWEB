from django.urls import path
from . import views

app_name = 'conciliaciones'

urlpatterns = [
    path('cargar/', views.cargar_estado_cuenta, name='cargar_estado_cuenta'),
    path('movimientos/<int:estado_id>/', views.lista_movimientos, name='lista_movimientos'),
    path('no_identificar/<int:mov_id>/', views.no_identificar, name='no_identificar'),
    # Agrega aquí la url para identificar con modal/AJAX
]