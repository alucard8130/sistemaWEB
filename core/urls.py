"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from areas import views
from principal.views import reporte_auditoria
from principal.views import bienvenida, reiniciar_sistema, respaldo_empresa_excel
from empresas.views import empresa_editar, empresa_eliminar, empresa_lista, empresa_crear
from locales.views import (
    crear_local, editar_local, eliminar_local, lista_locales, 
    locales_inactivos, reactivar_local)
from areas.views import (
    lista_areas, crear_area, editar_area, eliminar_area,
    areas_inactivas, reactivar_area)
from clientes.views import (
    carga_masiva_clientes, lista_clientes, crear_cliente, 
    editar_cliente, eliminar_cliente, plantilla_clientes_excel)

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
]
