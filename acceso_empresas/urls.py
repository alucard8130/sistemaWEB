from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Portal público
    path('login/', views.portal_login, name='acceso_login'),
    path('logout/', views.portal_logout, name='acceso_logout'),
    path('registro/', views.portal_registro, name='acceso_registro'),
    path('pago-pendiente/', views.pago_pendiente, name='acceso_pago_pendiente'),

    # Portal usuario de acceso
    path('', views.dashboard, name='acceso_dashboard'),
    path('empresa/<int:empresa_id>/activar/', views.cambiar_empresa_activa, name='acceso_cambiar_empresa'),
    path('solicitar/', views.solicitar_acceso_empresa, name='acceso_solicitar_empresa'),

    # Reportes
    path('reportes/estado-resultados/', views.reporte_estado_resultados, name='acceso_estado_resultados'),
    path('reportes/cobranza/', views.reporte_cobranza, name='acceso_cobranza'),
    path('reportes/gastos/', views.reporte_gastos, name='acceso_gastos'),

    # Superusuario
    path('admin/', views.superuser_panel, name='acceso_superuser_panel'),
    path('admin/aprobar/<int:acceso_id>/', views.aprobar_acceso, name='acceso_aprobar'),
    path('admin/permisos/<int:acceso_id>/', views.editar_permisos, name='acceso_editar_permisos'),

    path('admin/activar/<int:ua_pk>/', views.activar_usuario, name='acceso_activar_usuario'),

    path('checkout/', views.checkout_suscripcion, name='acceso_checkout'),
    path('pago-exitoso/', views.pago_exitoso, name='acceso_pago_exitoso'),
    path('webhook/', views.stripe_webhook_portal, name='acceso_stripe_webhook'),

    # Recuperación de contraseña
    path('password/reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='acceso_empresas/password_reset.html',
            email_template_name='acceso_empresas/password_reset_email.html',
            subject_template_name='acceso_empresas/password_reset_subject.txt',
            success_url='/portal/password/reset/done/'
        ),
        name='acceso_password_reset'),

    path('password/reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='acceso_empresas/password_reset_done.html'
        ),
        name='acceso_password_reset_done'),

    path('password/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='acceso_empresas/password_reset_confirm.html',
            success_url='/portal/password/reset/complete/'
        ),
        name='acceso_password_reset_confirm'),

    path('password/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='acceso_empresas/password_reset_complete.html'
        ),
        name='acceso_password_reset_complete'),

]