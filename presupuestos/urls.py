# presupuestos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.presupuesto_lista, name='presupuesto_lista'),
    path('nuevo/', views.presupuesto_nuevo, name='presupuesto_nuevo'),
    path('<int:pk>/editar/', views.presupuesto_editar, name='presupuesto_editar'),
    path('<int:pk>/eliminar/', views.presupuesto_eliminar, name='presupuesto_eliminar'),
    path('dashboard/', views.dashboard_presupuestal, name='dashboard_presupuestal'),
    path('presupuestos/matriz/', views.matriz_presupuesto, name='matriz_presupuesto'),
]
