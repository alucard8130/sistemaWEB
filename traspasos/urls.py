from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_traspasos, name='lista_traspasos'),
    path('nuevo/', views.nuevo_traspaso, name='nuevo_traspaso'),
    path('cancelar/<int:traspaso_id>/', views.cancelar_traspaso, name='cancelar_traspaso'),
]