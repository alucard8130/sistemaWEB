
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from escuelas.views import (
    LandingGesacCampusView,
    dashboard_admisiones,
    dashboard_inicio_escuela,
    estado_resultados_escuela,
    importar_altas_alumnos,
    importar_cartera_vencida,
    importar_ingresos_excel,
    importar_ingresos_fiserv,
    importar_roster_alumnos,
    matriz_presupuesto_ingresos_escuela,
    membresia_vencida_escuela,
    reporte_cartera_vencida_comparativo,
    webhook_hubspot_admisiones,
)
from principal.forms import EmpresaAuthenticationForm
from principal.views import registro_usuario, solicitar_pago_transferencia

urlpatterns = [
    path('acceso/', auth_views.LoginView.as_view(
        template_name='escuelas/login_escuela.html',
        authentication_form=EmpresaAuthenticationForm,
    ), name='login_escuela'),
    path('ingresos/importar/', importar_ingresos_excel, name='importar_ingresos_excel'),
    path('registro/', registro_usuario, name='registro_usuario_escuela'),
    path('dashboard/', dashboard_inicio_escuela, name='dashboard_inicio_escuela'),
    path('membresia-vencida/', membresia_vencida_escuela, name='membresia_vencida_escuela'),
    path('pagar/', solicitar_pago_transferencia, name='solicitar_pago_transferencia_escuela'),
    path('ingresos/importar-plataforma/', importar_ingresos_fiserv, name='importar_ingresos_fiserv'),
    path('webhooks/hubspot/<str:token>/<int:empresa_id>/', webhook_hubspot_admisiones, name='webhook_hubspot_admisiones'),
    path('admisiones/', dashboard_admisiones, name='dashboard_admisiones'),
    path('alumnos/importar-roster/', importar_roster_alumnos, name='importar_roster_alumnos'),
    path('alumnos/importar-altas/', importar_altas_alumnos, name='importar_altas_alumnos'),
    path('alumnos/cartera-vencida/', importar_cartera_vencida, name='importar_cartera_vencida'),
    path('presupuesto-ingresos/', matriz_presupuesto_ingresos_escuela, name='matriz_presupuesto_ingresos_escuela'),
    path('estado-resultados/', estado_resultados_escuela, name='estado_resultados_escuela'),
    path('cartera-vencida/comparativo/', reporte_cartera_vencida_comparativo, name='reporte_cartera_vencida_comparativo'),
    path(
        'escuelas/restaurar-password/',
        auth_views.PasswordResetView.as_view(
            template_name='escuelas/restaurar_password.html',
            email_template_name='escuelas/restaurar_password_email.txt',
            subject_template_name='escuelas/restaurar_password_subject.txt',
            success_url=reverse_lazy('escuela_password_reset_done'),
        ),
        name='escuela_password_reset',
    ),
    path(
        'escuelas/restaurar-password/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='escuelas/restaurar_password_done.html'
        ),
        name='escuela_password_reset_done',
    ),
    path(
        'escuelas/restaurar-password/confirmar/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='escuelas/restaurar_password_confirm.html',
            success_url=reverse_lazy('escuela_password_reset_complete'),
        ),
        name='escuela_password_reset_confirm',
    ),
    path(
        'escuelas/restaurar-password/completo/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='escuelas/restaurar_password_complete.html'
        ),
        name='escuela_password_reset_complete',
    ),
    path('landing/', LandingGesacCampusView.as_view(), name='landing_gesac_campus'),
]