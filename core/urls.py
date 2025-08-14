
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from areas import views
from principal.views import cancelar_suscripcion, crear_evento, crear_sesion_pago, eliminar_evento, enviar_correo_evento, guardar_datos_empresa, registro_usuario, reporte_auditoria, stripe_webhook
from principal.views import bienvenida, reiniciar_sistema, respaldo_empresa_excel
from empresas.views import empresa_editar, empresa_eliminar, empresa_lista, empresa_crear
from locales.views import (
    crear_local, editar_local, eliminar_local, lista_locales, 
    locales_inactivos, reactivar_local)
from areas.views import (
    lista_areas, crear_area, editar_area, eliminar_area,
    areas_inactivas, reactivar_area)
from clientes.views import (
    carga_masiva_clientes, clientes_inactivos, lista_clientes, crear_cliente, 
    editar_cliente, eliminar_cliente, plantilla_clientes_excel, reactivar_cliente)

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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 