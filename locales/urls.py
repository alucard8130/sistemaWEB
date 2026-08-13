from django.urls import path

from . import views

urlpatterns = [
    path('cuotas/incrementar/', views.incrementar_cuotas_locales, name='incrementar_c_locales'),
    path('carga-masiva/', views.carga_masiva_locales, name='carga_masiva_locales'),
    path('plantilla-locales/', views.plantilla_locales_excel, name='plantilla_locales_excel'),
    path('pools-vacancia/', views.lista_pools_vacancia, name='lista_pools_vacancia'),
    path('pools-vacancia/nuevo/', views.crear_pool_vacancia, name='crear_pool_vacancia'),
    path('pools-vacancia/<int:pool_id>/editar/', views.editar_pool_vacancia, name='editar_pool_vacancia'),
]
