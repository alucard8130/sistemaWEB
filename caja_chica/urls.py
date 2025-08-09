from django.urls import path
from . import views

urlpatterns = [
    path("fondeo/", views.fondeo_caja_chica, name="fondeo_caja_chica"),
    path(
        "registrar_gasto/",
        views.registrar_gasto_caja_chica,
        name="registrar_gasto_caja_chica",
    ),
    path('generar_vale/<int:fondeo_id>/', views.generar_vale_caja, name='generar_vale_caja'),
    path("lista_fondeos/", views.lista_fondeos, name="lista_fondeos"),
    path(
        "lista_gastos/", views.lista_gastos_caja_chica, name="lista_gastos_caja_chica"
    ),
    path("lista_vales/", views.lista_vales_caja_chica, name="lista_vales_caja_chica"),
    path(
        "detalle_fondeo/<int:fondeo_id>/", views.detalle_fondeo, name="detalle_fondeo"
    ),
    path(
        "imprimir_vale/<int:vale_id>/",
        views.imprimir_vale_caja,
        name="imprimir_vale_caja",
    ),
]
