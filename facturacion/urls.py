from django.urls import path
from . import views

urlpatterns = [
    path('nueva/', views.crear_factura, name='crear_factura'),
    path('lista/', views.lista_facturas, name='lista_facturas'),
    path('facturar-mes/', views.confirmar_facturacion, name='facturar_mes'),
    path('factura/<int:factura_id>/pago/', views.registrar_pago, name='registrar_pago'),
    path('pagos-origen/', views.pagos_por_origen, name='pagos_por_origen'),
    path('dashboard-saldos/', views.dashboard_saldos, name='dashboard_saldos'),
    path('dashboard-pagos/', views.dashboard_pagos, name='dashboard_pagos'),
    path('cartera/', views.cartera_vencida, name='cartera_vencida'),
    path('cartera/exportar/excel/', views.exportar_cartera_excel, name='exportar_cartera_excel'),
    path('pagos/exportar/excel/', views.exportar_pagos_excel, name='exportar_pagos_excel'),
    path('carga-masiva/', views.carga_masiva_facturas, name='carga_masiva_facturas'),
    path('plantilla-facturas/', views.plantilla_facturas_excel, name='plantilla_facturas_excel'),
    path('factura/<int:factura_id>/editar/', views.editar_factura, name='editar_factura'),
    path('factura/exportar/excel/', views.exportar_lista_facturas_excel, name='exportar_lista_facturas_excel'),
    path('carga-masiva-c/', views.carga_masiva_facturas_cobradas, name='carga_masiva_facturas_cobradas'),
    path('detalle/<int:pk>/', views.facturas_detalle, name='facturas_detalle'),
    path('otros-ingresos/nueva/', views.crear_factura_otros_ingresos, name='crear_factura_otros_ingresos'),
    path('otros-ingresos/lista/', views.lista_facturas_otros_ingresos, name='lista_facturas_otros_ingresos'),
    path('otros-ingresos/factura/<int:factura_id>/cobro/', views.registrar_cobro_otros_ingresos, name='registrar_cobro_otros_ingresos'),
    path('facturas/otros-ingresos/factura/<int:factura_id>/detalle/', views.detalle_factura_otros_ingresos, name='detalle_factura_otros_ingresos'),
 

    
]
