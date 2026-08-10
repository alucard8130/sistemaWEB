from django.urls import path

from . import views

urlpatterns = [
    path('operador/', views.sanitarios_operador, name='sanitarios_operador'),
    path('corte/', views.sanitarios_corte_diario, name='sanitarios_corte_diario'),
    path('configurar/', views.configurar_precio_sanitario, name='configurar_precio_sanitario'),
    path('caseta/<uuid:token>/', views.sanitarios_operador_caseta, name='sanitarios_operador_caseta'),
    path('casetas/', views.lista_casetas_sanitario, name='lista_casetas_sanitario'),
    # path('cortes-pendientes/', views.cortes_sanitario_pendientes, name='cortes_sanitario_pendientes'),
    path('boletos/cargar/', views.cargar_boletos_fisicos, name='cargar_boletos_fisicos'),
    path('gafetes/', views.lista_gafetes_acceso, name='lista_gafetes_acceso'),
    path('gafetes/<int:gafete_id>/toggle/', views.toggle_gafete_acceso, name='toggle_gafete_acceso'),
    path('gafetes/<int:gafete_id>/imprimir/', views.imprimir_gafete, name='imprimir_gafete'),
    # path('toallas/vender/', views.vender_toalla, name='vender_toalla'),
    path('toallas/lotes/', views.registrar_lote_toallas, name='registrar_lote_toallas'),
    path('toallas/lotes/<int:lote_id>/imprimir/', views.imprimir_entrega_lote, name='imprimir_entrega_lote'),
    path('cortes/<int:corte_id>/imprimir/', views.imprimir_corte_sanitario, name='imprimir_corte_sanitario'),
    path('depositos/', views.registrar_deposito_sanitarios, name='registrar_deposito_sanitarios'),
    path('caseta/<uuid:token>/cerrar-corte/', views.cerrar_corte_caseta, name='cerrar_corte_caseta'),
]