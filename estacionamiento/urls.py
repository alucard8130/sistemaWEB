from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_cortes, name='lista_cortes_estacionamiento'),
    path('nuevo/', views.crear_corte, name='crear_corte_estacionamiento'),
    path('<int:pk>/', views.detalle_corte, name='detalle_corte_estacionamiento'),
    path('<int:pk>/editar/', views.editar_corte, name='editar_corte_estacionamiento'),
    path('<int:pk>/eliminar/', views.eliminar_corte, name='eliminar_corte_estacionamiento'),
    path('<int:corte_pk>/importar/', views.importar_tickets, name='importar_tickets_estacionamiento'),
    path('<int:pk>/factura/', views.generar_factura_corte, name='generar_factura_corte_estacionamiento'),
]