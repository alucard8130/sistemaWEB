from django.urls import path
from . import views

urlpatterns = [
    path('nueva/', views.crear_factura, name='crear_factura'),
    path('lista/', views.lista_facturas, name='lista_facturas'),

]
