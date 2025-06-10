from django.urls import path
from . import views

urlpatterns = [
    path('', views.proveedor_lista, name='proveedor_lista'),
    path('nuevo/', views.proveedor_crear, name='proveedor_crear'),
    path('editar/<int:pk>/', views.proveedor_editar, name='proveedor_editar'),
]
