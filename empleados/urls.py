from django.urls import path
from . import views

urlpatterns = [
    path('', views.empleado_lista, name='empleado_lista'),
    path('nuevo/', views.empleado_crear, name='empleado_crear'),
    path('editar/<int:pk>/', views.empleado_editar, name='empleado_editar'),
]
