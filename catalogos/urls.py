from django.urls import path
from . import views

urlpatterns = [
    path('clientes-proveedores/carga-masiva/', views.carga_masiva_clientes_proveedores, name='carga_masiva_clientes_proveedores'),
    path('clientes-proveedores/plantilla/', views.plantilla_clientes_proveedores_excel, name='plantilla_clientes_proveedores_excel'),
]