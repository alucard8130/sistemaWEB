from os import path

from .views import reiniciar_sistema, reporte_auditoria

urlpatterns = [
    # otras rutas...
    path('reiniciar/', reiniciar_sistema, name='reiniciar_sistema'),
    path('auditoria/', reporte_auditoria, name='reporte_auditoria'),

]
