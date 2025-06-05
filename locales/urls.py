from django.urls import path
from . import views

urlpatterns = [
    path('cuotas/incrementar/', views.incrementar_cuotas_locales, name='incrementar_cuotas'),
]
