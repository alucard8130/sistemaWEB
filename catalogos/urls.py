from django.urls import path

from . import views

urlpatterns = [
    path('clientes-proveedores/carga-masiva/', views.carga_masiva_clientes_proveedores, name='carga_masiva_clientes_proveedores'),
    path('clientes-proveedores/plantilla/', views.plantilla_clientes_proveedores_excel, name='plantilla_clientes_proveedores_excel'),
    path('catalogo-cuentas/', views.lista_catalogo_cuentas, name='lista_catalogo_cuentas'),
    path('catalogo-cuentas/carga-masiva/', views.carga_masiva_catalogo_cuentas, name='carga_masiva_catalogo_cuentas'),
    path('catalogo-cuentas/plantilla/', views.plantilla_catalogo_cuentas_excel, name='plantilla_catalogo_cuentas_excel'),
    path('catalogo-cuentas/revisar/<int:sesion_id>/', views.revisar_carga_catalogo, name='revisar_carga_catalogo'),
    path('catalogo-cuentas/confirmar/<int:sesion_id>/', views.confirmar_carga_catalogo, name='confirmar_carga_catalogo'),
]