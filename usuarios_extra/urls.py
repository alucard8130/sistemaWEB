from django.urls import path

from . import views

urlpatterns = [
    path('', views.invitar_usuario_empresa, name='invitar_usuario_empresa'),
    path('invitacion/<str:token>/', views.aceptar_invitacion_usuario, name='aceptar_invitacion_usuario'),
]