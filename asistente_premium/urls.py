"""Rutas del asistente"""
from django.urls import path, include
#from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from .views import ChatView, ConversacionAsistenteViewSet

router = DefaultRouter()
router.register(r'conversaciones', ConversacionAsistenteViewSet, basename='conversacion')


urlpatterns = [
    # API REST
    path('api/', include(router.urls)),
    
    # Frontend Chat - Ahora permite iframe
    path('', ChatView.as_view(), name='asistente_chat'),
]