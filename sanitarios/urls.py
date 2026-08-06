from django.urls import path
from . import views

urlpatterns = [
    path('operador/', views.sanitarios_operador, name='sanitarios_operador'),
    path('corte/', views.sanitarios_corte_diario, name='sanitarios_corte_diario'),
    path('configurar/', views.configurar_precio_sanitario, name='configurar_precio_sanitario'),
    path('caseta/<uuid:token>/', views.sanitarios_operador_caseta, name='sanitarios_operador_caseta'),
    path('casetas/', views.lista_casetas_sanitario, name='lista_casetas_sanitario'),
    path('cortes-pendientes/', views.cortes_sanitario_pendientes, name='cortes_sanitario_pendientes'),
    path('boletos/cargar/', views.cargar_boletos_fisicos, name='cargar_boletos_fisicos'),
]