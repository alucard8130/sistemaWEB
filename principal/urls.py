from os import path
from .views import reiniciar_sistema

urlpatterns = [
    # otras rutas...
    path('reiniciar/', reiniciar_sistema, name='reiniciar_sistema'),
]
