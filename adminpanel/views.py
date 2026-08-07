
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render

from areas.models import AreaComun
from caja_chica.models import FondeoCajaChica, GastoCajaChica, ValeCaja
from clientes.models import Cliente
from empleados.models import Empleado
from empresas.models import Empresa
from facturacion.models import (
    CobroOtrosIngresos,
    Factura,
    FacturaOtrosIngresos,
    GrupoFacturacion,
    Pago,
    TipoCuotaHomologacion,
    TipoOtroIngreso,
)
from gastos.models import (
    CuentaContable,
    Gasto,
    GrupoGasto,
    PagoGasto,
    SubgrupoGasto,
    TipoGasto,
)
from locales.models import LocalComercial
from presupuestos.models import Presupuesto, PresupuestoIngreso
from principal.models import Aviso, Evento, PerfilUsuario, TemaGeneral, VisitanteAcceso
from proveedores.models import Proveedor
from sanitarios.models import BoletoFisico, CasetaOperador, CorteSanitario, UsoSanitario


#usuarios GESAC
@staff_member_required
def lista_usuarios_normales(request):
    usuarios = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, "adminpanel/lista_usuarios.html", {"usuarios": usuarios})

#usuarios condomninos
@staff_member_required
def lista_usuarios_visitantes(request):
    visitantes = VisitanteAcceso.objects.all().order_by('-id')
    return render(request, "adminpanel/lista_visitantes.html", {"visitantes": visitantes})

@staff_member_required
def toggle_activo_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.activo = not visitante.activo
    visitante.save()
    estado = "activado" if visitante.activo else "desactivado"
    messages.success(request, f"El visitante {visitante.username} ha sido {estado}.")

    # Enviar correo solo si se activó
    if visitante.activo:
        mensaje = (
            f"Hola {visitante.nombre},\n\n"
            "Tu cuenta ha sido activada por el sistema GESAC. Ya puedes ingresar: https://adminsoftheron.onrender.com/visitante/login/ \n\n"
            "Atentamente,\n"
            "El equipo de SoftHeron. \n\n" 
            "Gracias por utilizar nuestro sistema. Visita nuestra página web: \n"
            "https://paginaweb-ro9v.onrender.com \n"
            
        )
        send_mail(
            'Tu cuenta ha sido activada',
            mensaje,
            settings.EMAIL_HOST_USER, 
            [visitante.email],
            fail_silently=True,
        )
    return redirect('lista_usuarios_visitantes')

@staff_member_required
def toggle_reporte_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.acceso_api_reporte = not visitante.acceso_api_reporte
    visitante.save()
    return redirect('lista_usuarios_visitantes')



@user_passes_test(lambda u: u.is_superuser)
def resetear_empresa(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if request.method == "POST":
        # --- Facturación y cobranza ---
        Factura.objects.filter(empresa=empresa).delete()
        FacturaOtrosIngresos.objects.filter(empresa=empresa).delete()
        Pago.objects.filter(factura__empresa=empresa).delete()
        CobroOtrosIngresos.objects.filter(factura__empresa=empresa).delete()

        # --- Grupos de Facturación ---
        GrupoFacturacion.objects.filter(empresa=empresa).delete()

        # --- Caja Chica ---
        FondeoCajaChica.objects.filter(empresa=empresa).delete()
        GastoCajaChica.objects.filter(fondeo__empresa=empresa).delete()
        ValeCaja.objects.filter(fondeo__empresa=empresa).delete()

        # --- Propiedades y catálogos ---
        LocalComercial.objects.filter(empresa=empresa).delete()
        AreaComun.objects.filter(empresa=empresa).delete()
        Cliente.objects.filter(empresa=empresa).delete()
        Proveedor.objects.filter(empresa=empresa).delete()
        Empleado.objects.filter(empresa=empresa).delete()

        # --- Gastos (antes del catálogo contable, por la homologación) ---
        Gasto.objects.filter(empresa=empresa).delete()
        PagoGasto.objects.filter(gasto__empresa=empresa).delete()

        # --- Catálogo Contable (homologación) ---
        TipoGasto.objects.filter(empresa=empresa).delete()
        TipoCuotaHomologacion.objects.filter(empresa=empresa).delete()
        TipoOtroIngreso.objects.filter(empresa=empresa).delete()
        CuentaContable.objects.filter(empresa=empresa).delete()

        # --- Comunicación ---
        Evento.objects.filter(empresa=empresa).delete()
        TemaGeneral.objects.filter(empresa=empresa).delete()
        Aviso.objects.filter(empresa=empresa).delete()

        # --- Presupuestos ---
        Presupuesto.objects.filter(empresa=empresa).delete()
        PresupuestoIngreso.objects.filter(empresa=empresa).delete()

        # --- Control de Sanitarios ---
        UsoSanitario.objects.filter(empresa=empresa).delete()
        BoletoFisico.objects.filter(empresa=empresa).delete()
        CasetaOperador.objects.filter(empresa=empresa).delete()
        CorteSanitario.objects.filter(empresa=empresa).delete()

        # --- Contadores -- solo se les quita el acceso a ESTA empresa, nunca se borra su cuenta ---
        for perfil in PerfilUsuario.objects.filter(empresas_contador=empresa):
            perfil.empresas_contador.remove(empresa)
            if perfil.empresa_id == empresa.id:
                nueva_empresa = perfil.empresas_contador.first()
                perfil.empresa = nueva_empresa
                perfil.save(update_fields=["empresa"])

        # Puedes agregar más modelos relacionados aquí

        messages.success(request, f"Todos los datos de la empresa '{empresa.nombre}' han sido eliminados.")
        return redirect('bienvenida')

    return render(request, "adminpanel/resetear_empresa_confirm.html", {"empresa": empresa})