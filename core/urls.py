
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from adminpanel.views import lista_usuarios_normales, lista_usuarios_visitantes, toggle_activo_visitante, toggle_reporte_visitante
from areas import views
from caja_chica.views import comprobar_vale, detalle_fondeo, eliminar_fondeo, eliminar_gasto_caja, eliminar_vale_caja, exportar_fondeos_excel, exportar_gastos_caja_chica_excel, exportar_vales_caja_chica_excel, fondeo_caja_chica, generar_vale_caja, imprimir_vale_caja, lista_fondeos, lista_gastos_caja_chica, lista_vales_caja_chica, recibo_fondeo_caja, registrar_gasto_caja_chica
from empleados.views import exportar_incidencias_excel, incidencia_cancelar, incidencia_crear, incidencia_editar, incidencias_lista
from facturacion.views import consulta_facturas, exportar_consulta_facturas_excel, facturas_detalle, recibo_factura, recibo_factura_otras_cuotas, recibo_pago, recibo_pago_otras_cuotas
from gastos.views import descargar_reporte_retenciones_gastos, recibo_gasto, reporte_retenciones_gastos
from informes_financieros.views import cartera_vencida_por_origen, exportar_cartera_vencida_excel
from presupuestos.views import comparativo_anual_ingresos, comparativo_anual_total
from principal.views import actualizar_ticket, agregar_seguimiento, api_areas_por_empresa, api_avisos_empresa, api_dashboard_saldos_visitante, api_empresas_lista, api_estado_resultados, api_locales_por_empresa, api_reporte_ingresos_vs_gastos, aviso_crear, aviso_eliminar, avisos_lista, consulta_cfdis_facturama, crear_tema_y_enviar, create_payment_intent, descargar_cfdi_facturama, descargar_factura_timbrada, descargar_plantilla_estado_cuenta, eliminar_tema, enviar_recordatorio_morosidad, lista_temas, lista_tickets, crear_ticket, resultados_votacion, seleccionar_empresa, stripe_checkout_visitante, stripe_webhook_visitante, subir_csd_facturama, subir_estado_cuenta,tickets_asignados, cancelar_suscripcion, crear_evento, crear_sesion_pago, detalle_ticket, eliminar_evento, enviar_correo_evento, guardar_datos_empresa, registro_usuario, reporte_auditoria, stripe_webhook, timbrar_factura, timbrar_factura_otros_ingresos, visitante_consulta_facturas, visitante_factura_detalle, visitante_facturas_api, visitante_login, visitante_login_api, visitante_logout, visitante_registro_api, visitante_timbrar_factura, votar_tema_correo
from principal.views import bienvenida, reiniciar_sistema, respaldo_empresa_excel
from empresas.views import empresa_editar, empresa_eliminar, empresa_lista, empresa_crear
from locales.views import (
    crear_local, editar_local, eliminar_local, lista_locales, 
    locales_inactivos, reactivar_local)
from areas.views import (
    contrato_formulario, generar_contrato, lista_areas, crear_area, editar_area, eliminar_area,
    areas_inactivas, reactivar_area)
from clientes.views import (
    carga_masiva_clientes, clientes_inactivos, lista_clientes, crear_cliente, 
    editar_cliente, eliminar_cliente, plantilla_clientes_excel, reactivar_cliente)
from proveedores.views import carga_masiva_proveedores, eliminar_proveedor, plantilla_proveedores_excel
from publicidad.views import anuncios_api, solicitud_publicidad_api
from publicidad.views import anuncios_publicos
#from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView,)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', bienvenida, name='bienvenida'),
    path('empresas/nueva/', empresa_crear, name='empresa_crear'),
    path('empresas/', empresa_lista, name='empresa_lista'),
    path('empresas/editar/<int:pk>/', empresa_editar, name='empresa_editar'),
    path('empresas/eliminar/<int:pk>/', empresa_eliminar, name='empresa_eliminar'),
    path('locales/', lista_locales, name='lista_locales'),
    path('locales/crear/', crear_local, name='crear_local'),
    path('locales/editar/<int:pk>/', editar_local, name='editar_local'),
    path('locales/eliminar/<int:pk>/', eliminar_local, name='eliminar_local'),
    path('locales/inactivos/', locales_inactivos, name='locales_inactivos'),
    path('locales/reactivar/<int:pk>/', reactivar_local, name='reactivar_local'),
    path('areas/', lista_areas, name='lista_areas'),
    path('areas/crear/', crear_area, name='crear_area'),
    path('areas/editar/<int:pk>/', editar_area, name='editar_area'),
    path('areas/eliminar/<int:pk>/', eliminar_area, name='eliminar_area'),
    path('areas/inactivas/', areas_inactivas, name='areas_inactivas'),
    path('areas/reactivar/<int:pk>/', reactivar_area, name='reactivar_area'),
    path('clientes/', lista_clientes, name='lista_clientes'),
    path('clientes/crear/', crear_cliente, name='crear_cliente'),
    path('clientes/editar/<int:pk>/', editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:pk>/', eliminar_cliente, name='eliminar_cliente'),
    path('clientes/carga-masiva/', carga_masiva_clientes, name='carga_masiva_clientes'),
    path('clientes/plantilla-clientes/', plantilla_clientes_excel, name='plantilla_clientes_excel'),
    path('facturas/', include('facturacion.urls')),
    path('locales/', include('locales.urls')),
    path('areas/', include('areas.urls')),
    path('reiniciar-sistema/', reiniciar_sistema, name='reiniciar_sistema'),
    path('respaldo-empresa/', respaldo_empresa_excel, name='respaldo_empresa_excel'),
    path('auditoria/', reporte_auditoria, name='reporte_auditoria'),
    path('proveedores/', include('proveedores.urls')),
    path('empleados/', include('empleados.urls')),
    path('gastos/', include('gastos.urls')),
    path('presupuestos/', include('presupuestos.urls')),
    path('clientes/inactivos/', clientes_inactivos, name='clientes_inactivos'),
    path('clientes/reactivar/<int:pk>/', reactivar_cliente, name='reactivar_cliente'),
    path('informes/', include('informes_financieros.urls')),
    path('crear/', crear_evento, name='crear_evento'),
    path('evento/eliminar/<int:evento_id>/', eliminar_evento, name='eliminar_evento'),
    path('evento/enviar_correo/<int:evento_id>/', enviar_correo_evento, name='enviar_correo_evento'),
    path('registro/', registro_usuario, name='registro_usuario'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),    
    path('stripe/crear-sesion/', crear_sesion_pago, name='crear_sesion_pago'),
    path('stripe/cancelar-suscripcion/', cancelar_suscripcion, name='cancelar_suscripcion'),
    path('guardar-datos-empresa/', guardar_datos_empresa, name='guardar_datos_empresa'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path("fondeo/", fondeo_caja_chica, name="fondeo_caja_chica"),
    path("registrar_gasto/", registrar_gasto_caja_chica, name="registrar_gasto_caja_chica"),
    path("generar_vale/", generar_vale_caja, name="generar_vale_caja"),
    path("lista_fondeos/", lista_fondeos, name="lista_fondeos"),
    path("lista_gastos/", lista_gastos_caja_chica, name="lista_gastos_caja_chica"),
    path("lista_vales/", lista_vales_caja_chica, name="lista_vales_caja_chica"),
    path("detalle_fondeo/<int:fondeo_id>/", detalle_fondeo, name="detalle_fondeo"),
    path("imprimir_vale/<int:vale_id>/", imprimir_vale_caja, name="imprimir_vale_caja"),
    path('factura/<int:factura_id>/recibo/', recibo_factura, name='recibo_factura'),
    path('recibo_pago/<int:pago_id>/', recibo_pago, name='recibo_pago'),
    path('factura_otras_cuotas/<int:factura_id>/recibo/', recibo_factura_otras_cuotas, name='recibo_factura_otras_cuotas'),
    path('pago_otras_cuotas/<int:pago_id>/recibo/', recibo_pago_otras_cuotas, name='recibo_pago_otras_cuotas'),
    path('recibo_gasto/<int:gasto_id>/', recibo_gasto, name='recibo_gasto'),
    path("recibo_fondeo/<int:fondeo_id>/", recibo_fondeo_caja, name="recibo_fondeo"),
    path("tickets/", lista_tickets, name="lista_tickets"),
    path("tickets/crear/", crear_ticket, name="crear_ticket"),
    path("tickets/asignados/", tickets_asignados, name="tickets_asignados"),
    path("tickets/<int:ticket_id>/", detalle_ticket, name="detalle_ticket"),
    path("tickets/<int:ticket_id>/agregar_seguimiento/", agregar_seguimiento, name="agregar_seguimiento"),
    path("tickets/<int:ticket_id>/actualizar/", actualizar_ticket, name="actualizar_ticket"),
    path('seleccionar-empresa/', seleccionar_empresa, name='seleccionar_empresa'),
    path('incidencias/', incidencias_lista, name='incidencias_lista'),
    path('incidencias/nueva/', incidencia_crear, name='incidencia_crear'),
    path('incidencias/exportar/', exportar_incidencias_excel, name='exportar_incidencias_excel'),
    path('incidencias/<int:pk>/editar/', incidencia_editar, name='incidencia_editar'),
    path('incidencias/<int:pk>/cancelar/', incidencia_cancelar, name='incidencia_cancelar'),
    path('consulta-facturas/', consulta_facturas, name='consulta_facturas'),
    path('consulta-facturas/exportar/', exportar_consulta_facturas_excel, name='exportar_consulta_facturas_excel'),
    path('visitante/login/', visitante_login, name='visitante_login'),
    path('visitante/consulta/', visitante_consulta_facturas, name='visitante_consulta_facturas'),
    path('visitante/logout/', visitante_logout, name='visitante_logout'),
    path('visitante/factura/<int:factura_id>/detalle/',visitante_factura_detalle, name='visitante_factura_detalle'),
    path('visitante/factura/<int:factura_id>/stripe/', stripe_checkout_visitante, name='visitante_stripe_checkout'),
    path('visitante/stripe/webhook/', stripe_webhook_visitante, name='stripe_webhook_visitante'),
    path('votar/<str:token>/<str:respuesta>/', votar_tema_correo, name='votar_tema_correo'),
    path('votaciones/', lista_temas, name='lista_temas'),
    path('votaciones/resultados/<int:tema_id>/', resultados_votacion, name='resultados_votacion'),
    path('votaciones/crear/', crear_tema_y_enviar, name='crear_tema_y_enviar'),
    path('votaciones/eliminar/<int:tema_id>/', eliminar_tema, name='eliminar_tema'),
    path('conciliacion/subir/', subir_estado_cuenta, name='subir_estado_cuenta'),
    path('factura/timbrar/<int:pk>/', timbrar_factura, name='timbrar_factura'),
    path('factura/descargar-timbrada/<int:pk>/', descargar_factura_timbrada, name='descargar_factura_timbrada'),
    path('facturacion/subir-csd/', subir_csd_facturama, name='subir_csd_facturama'),
    path('facturacion/consulta-cfdis/', consulta_cfdis_facturama, name='consulta_cfdis_facturama'),
    path('facturacion/descargar-cfdi/<str:id>/', descargar_cfdi_facturama, name='descargar_cfdi_facturama'),
    path('otros-ingresos/timbrar/<int:pk>/', timbrar_factura_otros_ingresos, name='timbrar_factura_otros_ingresos'),
    path('visitante/timbrar-factura/<int:pk>/', visitante_timbrar_factura, name='visitante_timbrar_factura'),
    path('contrato/generar/<int:area_id>/', generar_contrato, name='generar_contrato'),
    path('carga-masiva/', carga_masiva_proveedores, name='carga_masiva_proveedores'),
    path('plantilla-proveedores/', plantilla_proveedores_excel, name='plantilla_proveedores_excel'),
    path('comparativo-anual/', comparativo_anual_total, name='comparativo_anual_total'),
    path('comparativo-anual-ingresos/', comparativo_anual_ingresos, name='comparativo_anual_ingresos'),
    path("vales/<int:vale_id>/eliminar/", eliminar_vale_caja, name="eliminar_vale_caja"),
    path("gastos_caja_chica/<int:gasto_id>/eliminar/",eliminar_gasto_caja, name="eliminar_gasto_caja"),
    path("fondeos/<int:fondeo_id>/eliminar/", eliminar_fondeo, name="eliminar_fondeo"),
    path("vales/<int:vale_id>/comprobar/", comprobar_vale, name="comprobar_vale"),
    path('estado-cuenta/', subir_estado_cuenta, name='subir_estado_cuenta'),
    path('estado-cuenta/descargar-plantilla/', descargar_plantilla_estado_cuenta, name='descargar_plantilla_estado_cuenta'),
    path('api/empresas/', api_empresas_lista, name='api_empresas_lista'),
    path('api/locales/<int:empresa_id>/', api_locales_por_empresa, name='api_locales_por_empresa'),
    path('api/areas/<int:empresa_id>/', api_areas_por_empresa, name='api_areas_por_empresa'),
    path('api/visitante/registro/', visitante_registro_api, name='visitante_registro_api'),
    path('api/visitante/login/', visitante_login_api, name='visitante_login_api'),
    path('api/visitante/facturas/',visitante_facturas_api, name='visitante_facturas_api'),
    path('api/visitante/reportes/', api_reporte_ingresos_vs_gastos, name='visitante_reportes_api'),
    path('api/visitante/cartera-vencida/', api_dashboard_saldos_visitante, name='api_dashboard_saldos_visitante'),
    path('api/visitante/avisos/', api_avisos_empresa, name='api_avisos_empresa'),
    path('api/visitante/estado-resultados/', api_estado_resultados, name='api_estado_resultados'),
    path('api/publicidad/anuncios/', anuncios_api, name='anuncios_api'),
    path('api/publicidad/solicitud/', solicitud_publicidad_api, name='solicitud_publicidad_api'),
    path('gastos_caja_chica/exportar/', exportar_gastos_caja_chica_excel, name='exportar_gastos_caja_chica_excel'),
    path('vales_caja_chica/exportar/', exportar_vales_caja_chica_excel, name='exportar_vales_caja_chica_excel'),
    path('fondeos/exportar/', exportar_fondeos_excel, name='exportar_fondeos_excel'),   
    path('proveedores/<int:pk>/eliminar/', eliminar_proveedor, name='eliminar_proveedor'),
    path('contrato/formulario/<int:area_id>/', contrato_formulario, name='contrato_formulario'),
    path('create-payment-intent/', create_payment_intent),
    path('enviar_recordatorio_morosidad/', enviar_recordatorio_morosidad, name='enviar_recordatorio_morosidad'),
    path('avisos/', avisos_lista, name='avisos_lista'),
    path('avisos/crear/', aviso_crear, name='aviso_crear'),
    path('avisos/eliminar/<int:aviso_id>/', aviso_eliminar, name='aviso_eliminar'),
    path('gastos/reporte-retenciones/', reporte_retenciones_gastos, name='reporte_retenciones_gastos'),
    path('gastos/reporte-retenciones/descargar/', descargar_reporte_retenciones_gastos, name='descargar_reporte_retenciones_gastos'),
    path('adminpanel/usuarios-normales/', lista_usuarios_normales, name='lista_usuarios_normales'),
    path('adminpanel/usuarios-visitantes/', lista_usuarios_visitantes, name='lista_usuarios_visitantes'),
    path('usuarios/visitantes/<int:visitante_id>/toggle-activo/', toggle_activo_visitante, name='toggle_activo_visitante'),
    path('usuarios/visitantes/<int:visitante_id>/toggle-reporte/', toggle_reporte_visitante, name='toggle_reporte_visitante'),
    path('publicidad/', anuncios_publicos, name='anuncios_publicos'),
    path('informes/cartera-vencida/', cartera_vencida_por_origen, name='cartera_vencida_por_origen'),
    path('cartera_vencida_excel/', exportar_cartera_vencida_excel, name='cartera_vencida_excel'),
]

    
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 
