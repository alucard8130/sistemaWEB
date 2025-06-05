from django.urls import path
from . import views

urlpatterns = [
    path('cuotas/incrementar/', views.incrementar_cuotas_locales, name='incrementar_c_locales'),
    path('carga-masiva/', views.carga_masiva_locales, name='carga_masiva'),
    path('plantilla-locales/', views.plantilla_locales_excel, name='plantilla_locales_excel'),
]
