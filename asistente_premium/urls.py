"""Rutas del asistente"""
from django.urls import include, path

#from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from .views import ChatView, ConversacionAsistenteViewSet, procesar_constancia_fiscal

router = DefaultRouter()
router.register(r'conversaciones', ConversacionAsistenteViewSet, basename='conversacion')



urlpatterns = [
     # Rutas específicas PRIMERO, para que no las capture el router genérico
    path('api/conversaciones/procesar_constancia_fiscal/', procesar_constancia_fiscal, name='procesar_constancia_fiscal'),

    # API REST
    path('api/', include(router.urls)),

    
    # Frontend Chat - Ahora permite iframe
    path('', ChatView.as_view(), name='asistente_chat'),
    
]