from os import path

from .views import crear_evento, eliminar_evento, registro_usuario, reiniciar_sistema, reporte_auditoria, stripe_webhook
urlpatterns = [
    # otras rutas...
    path('reiniciar/', reiniciar_sistema, name='reiniciar_sistema'),
    path('auditoria/', reporte_auditoria, name='reporte_auditoria'),
    path('registro/', registro_usuario, name='registro'), 
]
