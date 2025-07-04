from django.urls import path
from . import views

urlpatterns = [
    path('ingresos-vs-gastos/', views.reporte_ingresos_vs_gastos, name='reporte_ingresos_vs_gastos'),
    path('ingresos-estado-resultados/', views.estado_resultados, name='estado_resultados'),
    path('estado-resultados/exportar-excel/', views.exportar_estado_resultados_excel, name='exportar_estado_resultados_excel'),

    #path('ingresos-por-origen/', views.reporte_ingresos_por_origen, name='reporte_ingresos_por_origen'),
    #path('gastos-por-tipo/', views.reporte_gastos_por_tipo, name='reporte_gastos_por_tipo'),
]