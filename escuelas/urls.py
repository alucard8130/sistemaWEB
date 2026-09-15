
from django.contrib.auth import views as auth_views
from django.urls import path

from escuelas.views import importar_ingresos_excel
from principal.forms import EmpresaAuthenticationForm
from principal.views import registro_usuario

urlpatterns = [
    path('acceso/', auth_views.LoginView.as_view(
        template_name='escuelas/login_escuela.html',
        authentication_form=EmpresaAuthenticationForm,
    ), name='login_escuela'),
    path('ingresos/importar/', importar_ingresos_excel, name='importar_ingresos_excel'),
    path('registro/', registro_usuario, name='registro_usuario_escuela'),
]