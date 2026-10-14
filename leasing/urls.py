from django.urls import path

from . import views

app_name = "leasing"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("contratos/", views.contratos_lista, name="contratos"),
    path("contratos/<int:pk>/", views.contrato_detalle, name="contrato"),
    path("contratos/<int:pk>/activar/", views.contrato_activar, name="contrato_activar"),
    path("contratos/<int:pk>/generar-calendario/", views.contrato_generar_calendario, name="contrato_generar"),
    path("calendario/", views.calendario, name="calendario"),
    path("partidas/<int:pk>/aprobar/", views.partida_aprobar, name="partida_aprobar"),
    path("incidencias/", views.incidencias, name="incidencias"),
]
