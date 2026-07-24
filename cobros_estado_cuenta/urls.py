from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_sesiones, name='lista_sesiones_estado_cuenta'),
    path('subir/', views.subir_estado_cuenta, name='subir_estado_cuenta'),
    path('<int:pk>/revisar/', views.revisar_sesion, name='revisar_sesion_estado_cuenta'),
    path('movimiento/<int:movimiento_pk>/aplicar/', views.aplicar_movimiento, name='aplicar_movimiento_estado_cuenta'),
    path('<int:pk>/eliminar/', views.eliminar_sesion, name='eliminar_sesion_estado_cuenta'),
    path('convertir-preview/', views.convertir_pdf_preview, name='convertir_pdf_preview'),
]