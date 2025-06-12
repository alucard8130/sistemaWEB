from django.urls import path
from . import views

urlpatterns = [
    path('subgrupos/', views.subgrupos_gasto_lista, name='subgrupos_gasto_lista'),
    path('subgrupos/nuevo/', views.subgrupo_gasto_crear, name='subgrupo_gasto_crear'),
    path('tipos-gasto/', views.tipos_gasto_lista, name='tipos_gasto_lista'),
    path('tipos-gasto/nuevo/', views.tipo_gasto_crear, name='tipo_gasto_crear'),
    path('tipos-gasto/<int:pk>/editar/', views.tipo_gasto_editar, name='tipo_gasto_editar'),
    path('tipos-gasto/<int:pk>/eliminar/', views.tipo_gasto_eliminar, name='tipo_gasto_eliminar'),
    path('', views.gastos_lista, name='gastos_lista'),
    path('nuevo/', views.gasto_nuevo, name='gasto_nuevo'),
    path('<int:pk>/editar/', views.gasto_editar, name='gasto_editar'),
    path('<int:pk>/eliminar/', views.gasto_eliminar, name='gasto_eliminar'),
    path('gastos/<int:gasto_id>/pago/', views.registrar_pago_gasto, name='registrar_pago_gasto'),

]
