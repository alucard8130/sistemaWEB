from django.urls import path
from . import views

app_name = 'conciliaciones'

urlpatterns = [
    path('cargar/', views.cargar_estado_cuenta, name='cargar_estado'),
    path('conciliar/<int:estado_id>/', views.conciliar_estado_cuenta, name='conciliar'),
    path('resultado/<int:estado_id>/', views.resultado_conciliacion, name='resultado'),
]