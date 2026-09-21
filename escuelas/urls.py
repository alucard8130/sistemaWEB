
from django.contrib.auth import views as auth_views
from django.urls import path

from escuelas.views import (
    dashboard_admisiones,
    dashboard_inicio_escuela,
    importar_ingresos_excel,
    importar_ingresos_fiserv,
    membresia_vencida_escuela,
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
]