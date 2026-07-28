from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_traspasos, name='lista_traspasos'),
    path('nuevo/', views.nuevo_traspaso, name='nuevo_traspaso'),
    path('cancelar/<int:traspaso_id>/', views.cancelar_traspaso, name='cancelar_traspaso'),
    path('reporte_inversion/', views.reporte_inversion, name='reporte_inversion'),
    path('inversion/nuevo-movimiento/', views.nuevo_movimiento_inversion, name='nuevo_movimiento_inversion'),
    path('inversion/registrar-retencion/', views.registrar_retencion_inversion, name='registrar_retencion_inversion'),
    path('inversion/cancelar-movimiento/<int:traspaso_id>/', views.cancelar_movimiento_inversion, name='cancelar_movimiento_inversion'),
]