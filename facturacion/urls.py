from django.urls import path
from . import views

urlpatterns = [
    path('nueva/', views.crear_factura, name='crear_factura'),
    path('lista/', views.lista_facturas, name='lista_facturas'),
    #path('facturar-mes/', views.facturar_mes_actual, name='facturar_mes'),
    path('facturar-mes/', views.confirmar_facturacion, name='facturar_mes'),
    path('factura/<int:factura_id>/pago/', views.registrar_pago, name='registrar_pago'),
    path('pagos-origen/', views.pagos_por_origen, name='pagos_por_origen'),
    path('dashboard-saldos/', views.dashboard_saldos, name='dashboard_saldos'),


]
