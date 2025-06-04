from django.urls import path
from . import views

urlpatterns = [
    path('nueva/', views.crear_factura, name='crear_factura'),
    path('lista/', views.lista_facturas, name='lista_facturas'),
    #path('facturar-mes/', views.facturar_mes_actual, name='facturar_mes'),
    path('facturar-mes/', views.confirmar_facturacion, name='facturar_mes'),
]
