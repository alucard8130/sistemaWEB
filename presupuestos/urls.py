# presupuestos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    #path('', views.presupuesto_lista, name='presupuesto_lista'),
    path('nuevo/', views.presupuesto_nuevo, name='presupuesto_nuevo'),
    path('<int:pk>/editar/', views.presupuesto_editar, name='presupuesto_editar'),
    path('<int:pk>/eliminar/', views.presupuesto_eliminar, name='presupuesto_eliminar'),
    path('dashboard/', views.dashboard_presupuestal, name='dashboard_presupuestal'),
    path('presupuestos/matriz/', views.matriz_presupuesto, name='matriz_presupuesto'),
    #path('presupuestos/matriz_simple/', views.matriz_simple_presupuesto, name='matriz_simple_presupuesto'),
    path('presupuestos/exportar_excel/', views.exportar_presupuesto_excel, name='exportar_presupuesto_excel'),
    path('presupuestos/comparativo/', views.reporte_presupuesto_vs_gasto, name='reporte_presupuesto_vs_gasto'),
    path('comparativo-anio/', views.comparativo_presupuesto_anio, name='comparativo_presupuesto_anio'),
    path('comparativo-vs-gastos/', views.comparativo_presupuesto_vs_gastos, name='comparativo_presupuesto_vs_gastos'),
    path('descargar-plantilla-matriz-presupuesto/', views.descargar_plantilla_matriz_presupuesto, name='descargar_plantilla_matriz_presupuesto'),
    path('carga-masiva/', views.carga_masiva_presupuestos, name='carga_masiva_presupuestos'),
    #path('presupuesto-ingresos/comparativo/', views.presupuesto_ingresos_comparativo, name='presupuesto_ingresos_comparativo'),
    path('presupuestos/matriz-ingresos/', views.matriz_presupuesto_ingresos, name='matriz_presupuesto_ingresos'),
    path('presupuestos/comparativo-ing/', views.reporte_presupuesto_vs_ingreso, name='reporte_presupuesto_vs_ingreso'),
    path('carga-masiva-ingresos/', views.carga_masiva_presupuesto_ingresos, name='carga_masiva_presupuesto_ingresos'),
    path('descargar-plantilla-matriz-presupuesto-ingresos/', views.descargar_plantilla_matriz_presupuesto_ingresos, name='descargar_plantilla_matriz_presupuesto_ingresos'),
    path('presupuestos/copiar-gastos/', views.copiar_presupuesto_gastos_a_nuevo_anio, name='copiar_presupuesto_gastos_a_nuevo_anio'),
    path('presupuestos/copiar-ingresos/', views.copiar_presupuesto_ingresos_a_nuevo_anio, name='copiar_presupuesto_ingresos_a_nuevo_anio'),

]

