from django.urls import path

from . import views

urlpatterns = [
    path('gestion/', views.gestion_contratos_areas, name='gestion_contratos_areas'),
    path('<int:area_id>/', views.historial_contratos_area, name='historial_contratos_area'),
    path('<int:area_id>/nuevo/', views.crear_contrato_area, name='crear_contrato_area'),
    path('contrato/<int:contrato_id>/terminar/', views.terminar_contrato_area, name='terminar_contrato_area'),
    path('contrato/<int:contrato_id>/renovar-automatico/', views.renovar_contrato_automatico, name='renovar_contrato_automatico'),
    path('contrato/<int:contrato_id>/ventas/', views.capturar_ventas_contrato, name='capturar_ventas_contrato'),
    path('contrato/<int:contrato_id>/renovar/<str:modo>/', views.preparar_renovacion, name='preparar_renovacion'),
]