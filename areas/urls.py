from django.urls import path
from . import views

urlpatterns = [
    path('cuotas/incrementar/', views.incrementar_cuotas_areas, name='incrementar_c_areas'),
    path('area/<int:pk>/asignar_cliente/', views.asignar_cliente_area, name='asignar_cliente'),
    path('carga-masiva/', views.carga_masiva_areas, name='carga_masiva_areas'),
    path('plantilla-areas/', views.plantilla_areas_excel, name='plantilla_areas_excel'),
]
