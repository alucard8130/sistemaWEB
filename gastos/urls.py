from django.urls import path
from . import views

urlpatterns = [
    path('subgrupos/', views.subgrupos_gasto_lista, name='subgrupos_gasto_lista'),
    path('subgrupos/nuevo/', views.subgrupo_gasto_crear, name='subgrupo_gasto_crear'),
    path('tipos-gasto/', views.tipos_gasto_lista, name='tipos_gasto_lista'),
    path('tipos-gasto/nuevo/', views.tipo_gasto_crear, name='tipo_gasto_crear'),
    path('tipos-gasto/<int:pk>/editar/', views.tipo_gasto_editar, name='tipo_gasto_editar'),
    path('tipos-gasto/<int:pk>/eliminar/', views.tipo_gasto_eliminar, name='tipo_gasto_eliminar'),
    path('', views.gastos_lista, name='gastos_lista'),
    path('nuevo/', views.gasto_nuevo, name='gasto_nuevo'),
    path('<int:pk>/editar/', views.gasto_editar, name='gasto_editar'),
    path('<int:pk>/eliminar/', views.gasto_eliminar, name='gasto_eliminar'),
    path('gastos/<int:gasto_id>/pago/', views.registrar_pago_gasto, name='registrar_pago_gasto'),
    path('detalle/<int:pk>/', views.gasto_detalle, name='gasto_detalle'),
    path('reporte-pagos/', views.reporte_pagos_gastos, name='reporte_pagos_gastos'),
    path('gastos/dashboard-pagos/', views.dashboard_pagos_gastos, name='dashboard_pagos_gastos'),
    path('gastos/exportar-excel/', views.exportar_pagos_gastos_excel, name='exportar_pagos_gastos_excel'),
    path('subgrupos/', views.subgrupos_gasto_lista, name='subgrupos_gasto_lista'),
    path('subgrupos/<int:pk>/eliminar/', views.subgrupo_gasto_eliminar, name='subgrupo_gasto_eliminar'),
    path('gastos/carga-masiva/', views.carga_masiva_gastos, name='carga_masiva_gastos'),
    path('gastos/descargar-plantilla/', views.descargar_plantilla_gastos, name='descargar_plantilla_gastos'),

]
